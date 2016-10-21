# uftpd: small FTP server for ESP8266

**Intro**

Based on the work of chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
Christopher made a first uftp server script, which runs in foreground.
Paul made webrepl with the framework for background oprations, which then was used
also by Christopher to implement his utelnetsever code.
My task was to put all these pieces together and assemble this uftpd.py script,
which runs in background and acts as ftp server.
Due to its size, it either has to be integrated into the flash image as frozen
bytecode, by placing it into the esp8266/modules folder and performing a rebuild,
of it must be compiled into bytecode using mpy-cross and loaded as an .mpy file.
The frozen bytecode variant is preferred.

The server has some limitations:
- Passive mode only
- Binary mode only
- Limited wildcard support for the ls and nlist commands. Only `*` and `?` are
supported.
- Limited multi-session support. The server accepts multiple sessions, but only
one sessions command at a time is executed, which still allows interleaved actions.
- Not all ftp commands are implemented.

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
managers. These are test results with an arbitratry selected set:

**Linux**

- ftp: works for file & directory operations including support for the m* commands
- filezilla, fireftp: work fine, including loading into the editor & saving back.
Take care to limit the number of data session to 1.
- Nautilus 3.14.1: works mostly fine, including loading into the editor & saving back. Sometimes it does not close all client connections when the drive is ejected.
The reason for the problem seems to be that nautilus tries to load the top level
directory file list twice at the same time when returning to it from another directory.
That is too much for this little server.
- Thunar, Dolphin, Konqueror: work fine, including loading directly into e.g. an editor & saving back
- Chrome, Firefox: view/navigate directories & and view files

**Mac OS X, various Versions**

- ftp: works like on Linux
- Chrome, Firefox: view/navigate directories & and view files
- Finder: connects, but then locks in the attempt to display the
top level directory repeating attemps to open new sessions.
- FileZilla, FireFtp: Full operation, once proper configured (see above)

**Windows 10**

- File explorer: view/navigate directories & and copy files. For editing files you
have to copy them to your PC and back. Windows explorer does not always release the
connection when it is closed, which just results in a silent connection, which
is closed latest when Windows is shut down.
- FileZilla, FireFtp: Full operation, once proper configured (see above)
- ftp: practically useless, since passive mode is not supported and many
non-standard commands are used for the communication to the server,
like XPWD instead of PWD, XCWD instead of CWD.

**Android**

- ES File Manager: Works with file/directory view & navigate, file download,
file upload, file delete, file rename

**Windows 10 mobile**

- Metro file manager: Works with file/directory view & navigate, file download,
file upload, file delete, file rename. Slow and chaotic sequence of FTP commands.
Many unneeded re-login attempts.

**Conclusion**: All dedicated ftp clients except Windows ftp work fine, and most
of the file managers too. Windows ftp should work if active mode is implemented.

## Trouble shooting
The only trouble observed so far was clients not releasing the connections. You may tell
by the value of `uftp.client_list` which should be empty if not client is connected.
In that case you may restart the server with uftpd.restart(). If `uftd.client_busy`
is `True` when no client is connected, then restart the server with with
`uftpd.restart()`. If you want to see what happens at the server, you may set verbose to 2.
Just restart it with  `uftpd.restart(verbose=2)`,  or set `uftpd.verbose_l = 2`, and
`uftpd.verbose_l = 0` to stop control messages again.

## Files
uftpd.py: Server source file  
uftpd.mpy: Compiled version  
README.md: This one  
