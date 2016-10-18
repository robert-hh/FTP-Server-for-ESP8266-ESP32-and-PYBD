# uftpd: small FTP server for ESP8266

**Intro**

Based on the work of chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
Christopher made a first smal uftp server script, which runs in foreground.
Paul made webrepl with  framework for background oprations, which then was used
also by Christopher to implement his utelnetsever code.
My task was to put all these pieces together and assemble this uftpd.py script,
which runs in background and acts as ftp server.
Due to its size, it either has to be integrated into the fals image as frozen
bytecode, by placing it into the esp8266/modules folder and performing a rebuild,
of it must be compiled into bytecode using mpy-cross and loaded as an .mpy file.
The frozen bytecode variant is preferred.

The server has some limitations:
- Passive mode only
- Limited wildcard support for the ls and nlist commands. Only `*` and `?` are
supported.

## Startup

You'll start the server with:  

`import uftpd`  

The service will the immediately started at port 21. You may stop the service then with:  

`utfpd.stop()`  

When stopped or not started yet, start it manually with:

`uftpd.start([port = 21][, verbose = level])`   
or   
`uftpd.restart([port = 21][, verbose = level])`  

port is the port number (default 21)  
verbose controls the level of printed activity messages, values 0, 1, 2

You may use  
`uftd.restart([port = 21][, verbose = level])`  
as a shortcut for uftp.stop() and uftpd.start().

## Coverage
The server works well with most dedicated ftp clients, and many browsers and file
managers. These are test results:

**Linux**

- ftp: works for file & directory operations including support for the m* commands
- filezilla, fireftp: works fine, including loading into the editor & saving back.
Take care to limit the number of session to 1. With FileZilla you have to connect
using the server manager.
- Nautilus 3.14.1: works mostly, including loading into the editor & saving back. Sometimes
it locks.
- Thunar: works fine, including loading into the editor & saving back
- Dolphin: works fine, including loading into the editor & saving back
- Konqueror: works fine, including loading into the editor & saving back
- Chrome, Firefox: view/navigate directories & and view files

**Mac OS X, various Versions**

- ftp: works like on Linux
- Chrome, Firefox: view/navigate directories & and view files
- Finder: connects, but then locks in the attempt to display the
top level directory w/o any activity visible at the server.
- FileZilla etc: Full operation, once proper configured (see above)

**Windows 10**

- File explorer: view/navigate directories & and copy files. For editing files you have to copy them to your PC and back.  
Windows explorer does not always release the connection when it is closed, which
just results in a silent connection.
- ftp: practically useless, since passive mode is not supported and many
non-standard commands are used for the communication to the server,
like XPWD instead of PWD, XCWD instead of CWD.
- FileZilla etc: Full operation, once proper configured (see above)

## Trouble shooting
The only trouble observed so far was clients not releasing the connection, and then
further connections are refused. You may tell by the value of `uftp.client_busy`.
If the value is `True`, then the server still considers to be connected. In
that case just restart the server with uftpd.restart(), or set `uftd.client_busy`
to `False`
In case the you want to see what happens at the server, you may set verbose to 2.
just restart it with `uftpd.restart(verbose=2)`.
You can do that also w/o restarting the server by setting `uftpd.verbose_l = 2`,
and `uftpd.verbose_l = 0` to stop control messages again.
