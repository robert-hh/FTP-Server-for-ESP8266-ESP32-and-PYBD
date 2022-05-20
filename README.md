# uftpd: small FTP server for ESP8266, ESP32 and Pyboard D

**Intro**

## Capabilities
- The minimun necessary subset of commands are supported:
   `STOR`, `RETR`, `RNFR`, `RNTO` rename,  `DELE`, `MDTM`, `RMD`, `MKD`   `PWD`, `CDUP`:cd .., `SIZE f`:filesize, 
    `PASV`:passive mode, `PORT p`, `LIST`(aka `NLST`), `SITE` and `QUIT`. 

- Ommitted commands required as per RF5797 are `ABOR`, `ACCT`, `ALLO`, `APPE`, `MODE`, `REIN`, `REST`art, `STRU` and `HELP`.
  
- Recognized but ignored: `USER` and `PASS`.
- With the `SITE` command, the code in the payload MUST NOT be blocking, because that will block the device.
- No user authentication. Any user may log in without a password. 
- Binary (aka IMAGE) mode only i.e. no translations of NL to/from CRLF (Would be helpful going to/from MS Windows.)
- Limited multi-session support. 
    The server accepts multiple connections, but only
one session command at a time is served while the other sessions receive a 'busy'
response, which still allows interleaved actions.
- While the ftp server runs in the background and servicing requests, foreground tasks should not be run.
- ESP32 server is supported from version='v1.9.3-575 on. That version which introduced webrepl.

## Using

Due to the size limitations for ESP8266, ftpd either has to be integrated into the flash image as frozen
bytecode, by placing it into the esp8266/modules folder and performing a rebuild,
or compiled into bytecode using mpy-cross and loaded as an .mpy file.
The frozen bytecode variant is preferred.

## Starting/Stopping

Start the daemon using: `import uftpd`

The service will be started at port 21 in silent mode. 

Stop the daemon using: `uftpd.stop()`

To start with options use: `uftpd.start([port = 21][, verbose = level])`

port is the port number (default 21)
verbose >0 will print commands and activity messages and OSError if one occurs.

To restart with different options use: `uftd.restart([port = 21][, verbose = level])`

## Compatability
The server works well with most dedicated ftp clients, and most browsers and file
managers. These are test results with an arbitrary selected set:

**Linux**

- ftp: works for file & directory operations including support for the m* commands
- filezilla: including loading into the editor & saving back.
  Take care to limit the number of data session to 1.
- Nautilus: works mostly, including loading into the editor & saving back.
    Copying multiple files at once to the esp8266 fails, because nautilus tries
    to open multiple sessions for that purpose.
    Configure Nautilus with dconf-editor to show directory count for local dirs only.
    Once mounted, you can even open a terminal at that spot.
    The path is something like: /run/user/1000/gvfs/ftp:host=x.y.y.z.
- Thunar: works fine, including loading & saving of files.
    directly into e.g. an editor & saving back.
- Dolphin, Konqueror: work fine most of the time, including loading
    directly into e.g. an editor & saving back. 
- Chrome, Firefox: view/navigate directories & and view files

**Mac OS X, various Versions**

- Linux: ftp works 
- Chrome, Firefox: view/navigate directories & and view files
- FileZilla, Cyberduck: Full operation, once proper configured (see above).
Configure Cyberduck to transfer data in the command session.
- Finder: Fails. It connects, but then locks in the attempt to display the top level directory 
- Mountainduck: Works well


**Windows 10** (and Windows XP)

- ftp: supported. 
- File explorer: view/navigate directories & and copy files. 
    Windows explorer does not always release the
connection when it is closed, which just results in a silent connection, which
is closed latest when Windows is shut down.
- FileZilla, Cyberduck: Full operation, once proper configured (see above).
Configure Cyberduck to transfer data in the command session.
- WinSCP: works fine
- NppFTP - FTP extension to Notepad++: Works fine and is very convenient.
- Mountainduck: Works to some extent, but sometimes stumbles and takes a long
time to open a file.

**Android**

- ftp inside the terminal emulator termux: full operation.
- ftp-express
- Chrome: view/navigate directories & and view files

**IOS 9.1**

- FTP Client lite: works 

**Windows 10 mobile**

- Metro file manager: Works with file/directory view & navigate, file download,
file upload, file delete, file rename. Slow and chaotic sequence of FTP commands.

**Conclusion**: All dedicated ftp clients work fine, and most of the file managers.

## Trouble Shooting

uftpd supports verbose=1.

The only trouble observed was clients not releasing the connections. 
Check by the value of `uftp.client_list`, which should be empty if no client is connected, or 
by issuing the command rstat in ftp, which shows the number of connected clients.
Restart the server with uftpd.restart(). 
If `uftd.client_busy` is `True` when no client is connected, then restart the server with with
`uftpd.restart()`. 

## Files
- uftpd.py: for ESP8266 and ESP32 from version='v1.9.3-575 onward.
- ftpd.py: Simple version, works in foreground  to be used with all Micorpython versions. 
         Terminates when the client closes the
session. Only a single session is supported. 
    def ftpserver(port=21, timeout=None):

- ftpd_thread.py 
  Includes:
+++++++
    def ftpserver(not_stop_on_quit):
...
try:
   import _thread
    _thread.start_new_thread(ftpserver, ((True,)))
except:
    ftpserver(False)
++++++

- ftpd_pycom.py

- README.md: 

## Attribution
This version, 2022-04-06, comes from the github repository of   robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD

uftpd.py  
JD Smith Use a preallocated buffer, improve error handling, MDTM and  SITE support.
Jan Wieck Use separate FTP servers per socket for STAtion + AccessPoint mode.

Based on the work of RobertHH, chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
RobertHH  put all these pieces together and assembled an uftpd.py script,
which runs in background and acts as ftp server.
Christopher made a first uftp server script, which runs in foreground.
Paul made webrepl with the framework for background operations, which then was used
also by Christopher to implement his utelnetsever code.
/*
