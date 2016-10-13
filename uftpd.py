# 
# Small ftp server for ESP8266 Micropython
# Based on the work of chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
#
# The server accepts passive mode only. It runs in background.
# Start the server with:
#
# import uftpserver
# uftpserver.start([port = 21][, verbose = level])
# port is the port number (default 21)
# verbose controls the level of printed activity messages, values 0, 1, 2
#
# Copyright (c) 2016 Christopher Popp (initial ftp server framework)
# Copyright (c) 2016 Paul Sokolovsky (background execution control structure)
# Copyright (c) 2016 Robert Hammelrath (putting the pieces together and a few extensios)
# Distributed under MIT License
#
import socket
import network
import uos
import gc
from time import sleep_ms, localtime

ftpsocket = None
datasocket = None
command_client = None
DATA_PORT = 13333

STOR_flag = False
client_busy = False
verbose_l = 0
cwd = '/'
msg_250_OK = '250 OK\r\n'
msg_550_fail = '550 Failed\r\n'
fromname = None

month_name = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def send_list_data(path, data_client, full):
    try: # whether path is a directory name
        for fname in sorted(uos.listdir(path), key = str.lower):
            data_client.sendall(make_description(path, fname, full))
    except: # path may be a file name or pattern
        pattern = path.split("/")[-1].lower()
        path = path[:-(len(pattern) + 1)]
        if path == "": path = "/"
        for fname in sorted(uos.listdir(path), key = str.lower):
            if fncmp(fname.lower(), pattern) == True:
                data_client.sendall(make_description(path, fname, full))
                
def make_description(path, fname, full):
    global month_name
    if full:
        stat = uos.stat(get_absolute_path(path,fname))
        file_permissions = "drwxr-xr-x" if (stat[0] & 0o170000 == 0o040000) else "-rw-r--r--"
        file_size = stat[6]
        tm = localtime(stat[7])
        if tm[0] != localtime()[0]:
            description = "{}    1 owner group {:>10} {} {:2} {:>5} {}\r\n".format(
                file_permissions, file_size, month_name[tm[1]], tm[2], tm[0], fname)
        else:
            description = "{}    1 owner group {:>10} {} {:2} {:02}:{:02} {}\r\n".format(
                file_permissions, file_size, month_name[tm[1]], tm[2], tm[3], tm[4], fname)
    else:
        description = fname + "\r\n"
    return description
    
def send_file_data(path, data_client):
    with open(path, "r") as file:
        chunk = file.read(512)
        while len(chunk) > 0:
            data_client.sendall(chunk)
            chunk = file.read(512)

def save_file_data(path, data_client, mode):
    with open(path, mode) as file:
        chunk = data_client.read(512)
        while len(chunk) > 0:
            file.write(chunk)
            chunk = data_client.read(512)

def get_absolute_path(cwd, payload):
    # Just a few special cases "..", "." and ""
    # If payload start's with /, set cwd to / 
    # and consider the remainder a relative path
    if payload.startswith('/'):
        cwd = "/"
    for token in payload.split("/"):
        if token == '..':
            if cwd != '/':
                cwd = '/'.join(cwd.split('/')[:-1])
                if cwd == '': 
                    cwd = '/'
        elif token != '.' and token != '':
            if cwd == '/':
                cwd += token
            else:
                cwd = cwd + '/' + token
    return cwd

# compare fname against pattern. Pattern may contain
# wildcards ? and *.
def fncmp(fname, pattern):
    pi = 0
    si = 0
    while pi < len(pattern) and si < len(fname):
        if (fname[si] == pattern[pi]) or (pattern[pi] == '?'):
            si += 1
            pi += 1
        else:
            if pattern[pi] == '*': # recurse
                if pi == len(pattern.rstrip("*?")): # only wildcards left
                    return True
                while si < len(fname):
                    if fncmp(fname[si:], pattern[pi+1:]) == True:
                        return True
                    else:
                        si += 1
                return False
            else:
                return False
    if pi == len(pattern.rstrip("*"))  and si == len(fname):
        return True
    else:
        return False
        
def message(level, *args):
    global verbose_l
    if verbose_l >= level:
        for arg in args:
            print(arg, end = "")
        print()
        
def exec_ftp_command(cl):
    global command_client, client_busy
    global cwd, fromname
    global ftpsocket, datasocket
    global DATA_PORT, STOR_flag
    
    try:
        gc.collect()
        data_client = None
        data = cl.readline().decode("utf-8").rstrip("\r\n")
        if len(data) <= 0:
            # Empty packet, either close or ignore
            if STOR_flag == False and client_busy == True:
                cl.close()
                client_busy = False
                message(1, "Empty packet, connection closed")
            else:
                message(2, "Empty packet ignored")
                STOR_flag = False
            return
        
        STOR_flag = False
        command = data.split(" ")[0].upper()
        payload = data[len(command):].lstrip()
        path = get_absolute_path(cwd, payload)
        message(1, "Command={}, Payload={}, Path={}".format(command, payload, path))
        
        if command == "USER" or command == "PASS":
            cl.sendall("230 Logged in.\r\n")
        elif command == "SYST":
            cl.sendall("215 UNIX Type: L8\r\n")
        elif command == "NOOP":
            cl.sendall("200 OK\r\n")
        elif command == "FEAT":
            cl.sendall("211 no-features\r\n")
        elif command == "QUIT":
            cl.sendall('221 Bye.\r\n')
            cl.close()
            client_busy = False
        elif command == "PWD":
            cl.sendall('257 "{}"\r\n'.format(cwd))
        elif command == "CWD":
            try:
                files = uos.listdir(path)
                cwd = path
                cl.sendall(msg_250_OK)
            except:
                cl.sendall(msg_550_fail)
        elif command == "CDUP":
            cwd = get_absolute_path(cwd, "..")
            cl.sendall(msg_250_OK)
        elif command == "TYPE":
            # probably should switch between binary and not
            cl.sendall('200 Transfer mode set\r\n')
        elif command == "SIZE":
            try:
                size = uos.stat(path)[6]
                cl.sendall('213 {}\r\n'.format(size))
            except:
                cl.sendall(msg_550_fail)
        elif command == "PASV":
            addr = network.WLAN().ifconfig()[0]
            cl.sendall('227 Entering Passive Mode ({},{},{}).\r\n'.format(
                addr.replace('.',','), DATA_PORT>>8, DATA_PORT%256))
        elif command == "LIST" or command == "NLST":
            if not payload.startswith("-"):
                place = path
            else: 
                place = cwd
            try:
                data_client, data_addr = datasocket.accept()
                message(2, "FTP Data connection from:", data_addr)
                cl.sendall("150 Here comes the directory listing.\r\n")
                send_list_data(place, data_client, command == "LIST" or payload.startswith("-l"))
                cl.sendall("226 Listed.\r\n")
            except:
                cl.sendall(msg_550_fail)
        elif command == "RETR":
            try:
                data_client, data_addr = datasocket.accept()
                message(2, "FTP Data connection from:", data_addr)
                send_file_data(path, data_client)
                cl.sendall("150 Opening data connection.\r\n")
                cl.sendall("226 Transfer complete.\r\n")
            except:
                cl.sendall(msg_550_fail)
        elif command == "STOR":
            try:
                data_client, data_addr = datasocket.accept()
                message(2, "FTP Data connection from:", data_addr)
                cl.sendall("150 Ok to send data.\r\n")
                save_file_data(path, data_client, "w")
                cl.sendall("226 Transfer complete.\r\n")
                STOR_flag = True
            except:
                cl.sendall(msg_550_fail)
        elif command == "APPE":
            try:
                data_client, data_addr = datasocket.accept()
                message(2, "FTP Data connection from:", data_addr)
                cl.sendall("150 Ok to send data.\r\n")
                save_file_data(path, data_client, "a")
                cl.sendall("226 Transfer complete.\r\n")
            except:
                cl.sendall(msg_550_fail)
        elif command == "DELE":
            try:
                uos.remove(path)
                cl.sendall(msg_250_OK)
            except:
                cl.sendall(msg_550_fail)
        elif command == "RNFR":
                fromname = path
                cl.sendall("350 Rename from\r\n")
        elif command == "RNTO":
                if fromname is not None: 
                    try:
                        uos.rename(fromname, path)
                        cl.sendall(msg_250_OK)
                    except:
                        cl.sendall(msg_550_fail)
                else:
                    cl.sendall(msg_550_fail)
                fromname = None
        elif command == "RMD":
            try:
                uos.rmdir(path)
                cl.sendall(msg_250_OK)
            except:
                cl.sendall(msg_550_fail)
        elif command == "MKD":
            try:
                uos.mkdir(path)
                cl.sendall(msg_250_OK)
            except:
                cl.sendall(msg_550_fail)
        else:
            cl.sendall("502 Unsupported command.\r\n")
            message(2, "Unsupported command {} with payload {}".format(command, payload))
    # handle unexpected errors
    # close all connections & exit
    except Exception as err:
        message(0, "Exception in exec_ftp_command: ", err)  
        cl.close()
        client_busy = False
    if data_client is not None:
        data_client.close()

def accept_ftp_connect(ftpsocket):
    global command_client, client_busy
    global cwd, fromname

    if client_busy == False:
        # Accept new calls for the server only if the previous client has finished
        client_busy = True
        command_client, remote_addr = ftpsocket.accept()
        command_client.settimeout(300) # 5 minutes timeout
        message(1, "FTP connection from:", remote_addr)
        cwd = '/'
        fromname = None
        command_client.setsockopt(socket.SOL_SOCKET, 20, exec_ftp_command)
        command_client.sendall("220 Hello, this is the ESP8266.\r\n")
    else:
        # accept and close immediately
        temp_client, remote_addr = ftpsocket.accept()
        temp_client.close()
        message(2, "Rejected FTP connection from:", remote_addr)

def stop():
    global ftpsocket, datasocket
    global command_client, client_busy

    if command_client is not None:
        command_client.close()
        command_client = None
    client_busy = False
    if ftpsocket is not None:
        ftpsocket.close()
    if datasocket is not None:
        datasocket.close()
        

# start listening for ftp connections on port 21
def start(port=21, verbose = 0):
    global ftpsocket, datasocket
    global DATA_PORT
    global verbose_l
    
    verbose_l = verbose

    ftpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    datasocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ftpsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    datasocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ftpsocket.bind(socket.getaddrinfo("0.0.0.0", port)[0][4])
    datasocket.bind(socket.getaddrinfo("0.0.0.0", DATA_PORT)[0][4])

    ftpsocket.listen(0)
    ftpsocket.settimeout(60)
    datasocket.listen(0)
    datasocket.settimeout(10)
    ftpsocket.setsockopt(socket.SOL_SOCKET, 20, accept_ftp_connect)
    
    for i in (network.AP_IF, network.STA_IF):
        wlan = network.WLAN(i)
        if wlan.active():
            print("FTP server started on {}:{}".format(wlan.ifconfig()[0], port))

def restart(port=21, verbose = 0):
    stop()
    sleep_ms(200)
    start(port, verbose)
    
start()
