#
# Small ftp server for ESP8266 Micropython
# Based on the work of chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
#
# The server accepts passive mode only. It runs in background.
# Start the server with:
#
# import ftpd
# ftpd.start([port = 21][, verbose = level])
#
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

# constant definitions
CHUNK_SIZE = const(200)
SO_REGISTER_CALLBACK = const(20)
COMMAND_TIMEOUT = const(300)
DATA_TIMEOUT = const(100)
DATA_PORT = const(13333)

# Global variables
ftpsocket = None
datasocket = None
client_list = []
verbose_l = 0
client_busy = False
my_ip_addr = network.WLAN().ifconfig()[0]

month_name = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

class FTP_client:

    def __init__(self, ftpsocket):
        self.command_client, self.remote_addr = ftpsocket.accept()
        self.command_client.settimeout(COMMAND_TIMEOUT)
        log_msg(1, "FTP connection from:", self.remote_addr)
        self.command_client.setsockopt(socket.SOL_SOCKET, SO_REGISTER_CALLBACK, self.exec_ftp_command)
        self.command_client.sendall("220 Hello, this is the ESP8266.\r\n")
        self.cwd = '/'
        self.fromname = None
        self.data_addr = None
        self.data_port = 20
        self.data_mode = False

    def send_list_data(self, path, data_client, full):
        try:
            for fname in uos.listdir(path):
                data_client.sendall(self.make_description(path, fname, full))
        except: # path may be a file name or pattern
            path, pattern = self.split_path(path)
            try:
                for fname in uos.listdir(path):
                    if self.fncmp(fname, pattern) == True:
                        data_client.sendall(self.make_description(path, fname, full))
            except:
                pass
        
    def make_description(self, path, fname, full):
        global month_name
        if full:
            stat = uos.stat(self.get_absolute_path(path, fname))
            file_permissions = "drwxr-xr-x" if (stat[0] & 0o170000 == 0o040000) else "-rw-r--r--"
            file_size = stat[6]
            tm = localtime(stat[7])
            if tm[0] != localtime()[0]:
                description = "{} 1 owner group {:>10} {} {:2} {:>5} {}\r\n".format(
                    file_permissions, file_size, month_name[tm[1]], tm[2], tm[0], fname)
            else:
                description = "{} 1 owner group {:>10} {} {:2} {:02}:{:02} {}\r\n".format(
                    file_permissions, file_size, month_name[tm[1]], tm[2], tm[3], tm[4], fname)
        else:
            description = fname + "\r\n"
        return description
        
    def send_file_data(self, path, data_client):
        with open(path, "r") as file:
            chunk = file.read(CHUNK_SIZE)
            while len(chunk) > 0:
                data_client.sendall(chunk)
                chunk = file.read(CHUNK_SIZE)
            data_client.close()
            return None
                

    def save_file_data(self, path, data_client, mode):
        with open(path, mode) as file:
            chunk = data_client.read(CHUNK_SIZE)
            while len(chunk) > 0:
                file.write(chunk)
                chunk = data_client.read(CHUNK_SIZE)
            data_client.close()
            return None

    def get_absolute_path(self, cwd, payload):
        # Just a few special cases "..", "." and ""
        # If payload start's with /, set cwd to / 
        # and consider the remainder a relative path
        if payload.startswith('/'):
            cwd = "/"
        for token in payload.split("/"):
            if token == '..':
                cwd = self.split_path(cwd)[0]
            elif token != '.' and token != '':
                if cwd == '/':
                    cwd += token
                else:
                    cwd = cwd + '/' + token
        return cwd
        
    def split_path(self, path): # instead of path.rpartition('/')
        tail = path.split('/')[-1]
        head = path[:-(len(tail) + 1)]
        return ('/' if head == '' else head, tail)

    # compare fname against pattern. Pattern may contain
    # the wildcards ? and *.
    def fncmp(self, fname, pattern):
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
                        if self.fncmp(fname[si:], pattern[pi + 1:]) == True:
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

    def open_dataclient(self):
        if self.data_mode == False: # passive mode
            data_client, self.data_addr = datasocket.accept()
        else: # active mode
            data_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_client.settimeout(DATA_TIMEOUT)
            data_client.connect((self.data_addr, self.data_port))
        log_msg(1, "FTP Data connection from/to:", self.data_addr)
        return data_client

    @staticmethod        
    def exec_ftp_command(cl):
        global datasocket
        global client_busy
        global my_ip_addr
        
        try:
            gc.collect()

            # since there is no self as function argument, get it from the list
            self = get_client(cl)
            if self == None: # Not found, which is a hard fail
                cl.sendall("520 No client instance\r\n")
                return

            data = cl.readline().decode("utf-8").rstrip("\r\n")
            if len(data) <= 0:
                # No data, close
                # This part is NOT CLEAN, there is still a chance that a closing data connection
                # will be signalled as closing command connection; might be a bug
                cl.close()
                cl.setsockopt(socket.SOL_SOCKET, SO_REGISTER_CALLBACK, None)
                remove_client(cl)
                log_msg(2, "*** No data, assume QUIT")
                return

            command = data.split(" ")[0].upper()

            if client_busy == True: # check if another client is busy
                # log_msg(2, "*** Device busy, command {} rejected".format(command))
                cl.sendall("400 Device busy.\r\n") # tell so the remote client
                return # and quit
            client_busy = True # now it's my turn
                
            data_client = None
            payload = data[len(command):].lstrip() # partition is missing
            path = self.get_absolute_path(self.cwd, payload)
            log_msg(1, "Command={}, Payload={}".format(command, payload))
            if command[0] == 'X': # map the X... commands to its counterpart
                command = command[1:] # by dropping the X
            
            if command == "USER":
                self.user = payload
                cl.sendall("230 Logged in.\r\n")
            elif command == "PASS":
                cl.sendall("230 Logged in.\r\n")
            elif command == "SYST":
                cl.sendall("215 UNIX Type: L8\r\n")
            elif command in ("TYPE", "NOOP", "ABOR"): # just accept & ignore
                cl.sendall('200 OK\r\n')
            elif command == "QUIT":
                cl.sendall('221 Bye.\r\n')
                cl.close()
                cl.setsockopt(socket.SOL_SOCKET, SO_REGISTER_CALLBACK, None)
                remove_client(cl)
            elif command == "PWD":
                cl.sendall('257 "{}"\r\n'.format(self.cwd))
            elif command == "CWD":
                try:
                    if (uos.stat(path)[0] & 0o170000) == 0o040000:
                        self.cwd = path
                        cl.sendall('250 OK\r\n')
                    else:
                        cl.sendall('550 Fail\r\n')
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "CDUP":
                self.cwd = self.get_absolute_path(self.cwd, "..")
                cl.sendall('250 OK\r\n')
            elif command == "SIZE":
                try:
                    cl.sendall('213 {}\r\n'.format(uos.stat(path)[6]))
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "STAT":
                if payload == "":
                    cl.sendall("211-({}) MicroPython FTP Server status\r\n"
                               "    Connected to ({})\r\n"
                               "    Logged in as {}\r\n"
                               "    TYPE: Binary STRU: File MODE: Stream\r\n"
                               "    Session timeout 300\r\n"
                               "    Client count is {}\r\n"
                               "211 End of Status\r\n".format(
                               my_ip_addr, self.remote_addr[0], self.user, len(client_list)))
                else:
                    cl.sendall("213- Here comes the directory listing.\r\n")
                    self.send_list_data(path, cl, True)
                    cl.sendall("213 Done.\r\n")
            elif command == "PASV":
                cl.sendall('227 Entering Passive Mode ({},{},{}).\r\n'.format(
                    my_ip_addr.replace('.',','), DATA_PORT>>8, DATA_PORT%256))
                self.data_mode = False
            elif command == "PORT":
                items = payload.split(",")
                if len(items) >= 6:
                    self.data_addr = '.'.join(items[:4])
                    self.data_port = int(items[4]) * 256 + int(items[5])
                    cl.sendall('200 OK\r\n')
                    self.data_mode = True
                else:
                    cl.sendall('504 Fail\r\n')
            elif command == "LIST" or command == "NLST":
                if payload.startswith("-"):
                    option = payload.split()[0]
                    path = self.get_absolute_path(self.cwd, payload[len(option) + 1:])
                else:
                    option = ""
                try:
                    data_client = self.open_dataclient()
                    cl.sendall("150 Here comes the directory listing.\r\n")
                    self.send_list_data(
                        self.cwd if payload == "" else path, 
                        data_client,
                        command == "LIST" or 'l' in option)
                    cl.sendall("226 Done.\r\n")
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "RETR":
                try:
                    data_client = self.open_dataclient()
                    cl.sendall("150 Opening data connection.\r\n")
                    data_client = self.send_file_data(path, data_client)
                    cl.sendall("226 Transfer complete.\r\n")
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "STOR" or command == "APPE":
                try:
                    data_client = self.open_dataclient()
                    cl.sendall("150 Ok to send data.\r\n")
                    data_client = self.save_file_data(
                                    path, data_client, "w" if command == "STOR" else "a")
                    cl.sendall("226 Transfer complete.\r\n")
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "DELE":
                try:
                    uos.remove(path)
                    cl.sendall('250 OK\r\n')
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "RNFR":
                try:
                    uos.stat(path) # just test if the name exists, exception if not
                    self.fromname = path
                    cl.sendall("350 Rename from\r\n")
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "RNTO":
                    try:
                        uos.rename(self.fromname, path)
                        cl.sendall('250 OK\r\n')
                    except:
                        cl.sendall('550 Fail\r\n')
                    self.fromname = None
            elif command == "RMD":
                try:
                    uos.rmdir(path)
                    cl.sendall('250 OK\r\n')
                except:
                    cl.sendall('550 Fail\r\n')
            elif command == "MKD":
                try:
                    uos.mkdir(path)
                    cl.sendall('250 OK\r\n')
                except:
                    cl.sendall('550 Fail\r\n')
            else:
                cl.sendall("502 Unsupported command.\r\n")
                # log_msg(2, "Unsupported command {} with payload {}".format(command, payload))
        # handle unexpected errors
        except Exception as err:
            log_msg(1, "Exception in exec_ftp_command: {}".format(err))
        # tidy up before leaving
        if data_client is not None:
            data_client.close()
        client_busy = False
            
def log_msg(level, *args):
    global verbose_l
    if verbose_l >= level:
        for arg in args:
            print(arg, end = "")
        print()

# look for the client in client_list
def get_client(cl):
    for client in client_list:
        if client.command_client == cl:
            return client
    return None
    
# remove a client from the list
def remove_client(cl):
    for i, client in enumerate(client_list):
        if client.command_client == cl:
            del client_list[i]
            break

def accept_ftp_connect(ftpsocket):
    # Accept new calls for the server
    try:
        client_list.append(FTP_client(ftpsocket))
    except:
        log_msg(1, "Attempt to connect failed")
        pass

def stop():
    global ftpsocket, datasocket
    global client_list
    global client_busy

    for client in client_list:
        client.command_client.close()
    del client_list
    client_list = []
    client_busy = False
    if ftpsocket is not None:
        ftpsocket.setsockopt(socket.SOL_SOCKET, SO_REGISTER_CALLBACK, None)
        ftpsocket.close()
    if datasocket is not None:
        datasocket.close()

# start listening for ftp connections on port 21
def start(port=21, verbose = 0):
    global ftpsocket, datasocket
    global verbose_l
    global client_list
    global client_busy
    
    verbose_l = verbose
    client_list = []
    client_busy = False

    ftpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    datasocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ftpsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    datasocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ftpsocket.bind(socket.getaddrinfo("0.0.0.0", port)[0][4])
    datasocket.bind(socket.getaddrinfo("0.0.0.0", DATA_PORT)[0][4])

    ftpsocket.listen(0)
    datasocket.listen(0)

    datasocket.settimeout(10)
    ftpsocket.setsockopt(socket.SOL_SOCKET, SO_REGISTER_CALLBACK, accept_ftp_connect)
    
    for i in (network.AP_IF, network.STA_IF):
        wlan = network.WLAN(i)
        if wlan.active():
            print("FTP server started on {}:{}".format(wlan.ifconfig()[0], port))

def restart(port=21, verbose = 0):
    stop()
    sleep_ms(200)
    start(port, verbose)
    
start()
