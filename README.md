# uftpd: small FTP server for ESP8266 and ESP32

**Intro**

Based on the work of chrisgp - Christopher Popp and pfalcon - Paul Sokolovsky
Christopher made a first uftp server script, which runs in foreground.
Paul made webrepl with the framework for background operations, which then was used
also by Christopher to implement his utelnetsever code.
My task was to put all these pieces together and assemble this uftpd.py script,
which runs in background and acts as ftp server.
Due to its size, it either has to be integrated into the flash image as frozen
bytecode, by placing it into the esp8266/modules folder and performing a rebuild,
or it must be compiled into bytecode using mpy-cross and loaded as an .mpy file.
The frozen bytecode variant is preferred.

The server has some limitations:
- Binary mode only
- Limited multi-session support. The server accepts multiple sessions, but only
one session command at a time is served while the other sessions receive a 'busy'
response, which still allows interleaved actions.
- No user authentication. Any user may log in without a password. User
authentication may be added easily, if required.
- Not all ftp commands are implemented.
- ESP8266 is **NOT** a multitasking platform and the system calls are NOT re-entrant.
Even when the ftp server sits in background and can serve requests, **no
foreground tasks should run at that time**, especially if they execute system calls.
The effects is hardly to predict, although most of the time the device simply
crashes.
- ESP32 The server is supported from version='v1.9.3-575 on. That is the version
which introduced webrepl.


## Start-up

You'll start the server with:

`import uftpd`

The service will immediately be started at port 21 in silent mode. You may
stop the service then with:

`utfpd.stop()`

When stopped or not started yet, start it manually with:

`uftpd.start([port = 21][, verbose = level])`
or
`uftpd.restart([port = 21][, verbose = level])`

port is the port number (default 21)
verbose controls the level of printed activity messages, values 0 .. 2

You may use
`uftd.restart([port = 21][, verbose = level])`
as a shortcut for uftp.stop() and uftpd.start().

## Coverage
The server works well with most dedicated ftp clients, and most browsers and file
managers. These are test results with an arbitrary selected set:

**Linux**

- ftp: works for file & directory operations including support for the m* commands
- filezilla, fireftp: work fine, including loading into the editor & saving back.
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
directly into e.g. an editor & saving back. But no obvious disconnect.
- Chrome, Firefox: view/navigate directories & and view files

**Mac OS X, various Versions**

- ftp: works like on Linux
- Chrome, Firefox: view/navigate directories & and view files
- FileZilla, FireFtp, Cyberduck: Full operation, once proper configured (see above).
Configure Cyberduck to transfer data in the command session.
- Finder: Fails. It connects, but then locks in the attempt to display the
top level directory repeating attempts to open new sessions. Finder needs
full multi-session support, and never closes sessions properly.
- Mountainduck: Works well, including proper disconnect when closing.


**Windows 10** (and Windows XP)

- ftp: supported. Be aware that the Windows variant of ftp differs slightly
from the Linux variant, but the most used commands are the same.
- File explorer: view/navigate directories & and copy files. For editing files you
have to copy them to your PC and back. Windows explorer does not always release the
connection when it is closed, which just results in a silent connection, which
is closed latest when Windows is shut down.
- FileZilla, FireFtp, Cyberduck: Full operation, once proper configured (see above).
Configure Cyberduck to transfer data in the command session.
- WinSCP: works fine
- NppFTP - FTP extension to Notepad++: Works fine and is very convenient.
- Mountainduck: Works to some extent, but sometimes stumbles and takes a long
time to open a file.

**Android tablet**

- ftp inside the terminal emulator termux: full operation.
- ES File Manager: Works with file/directory view & navigate, file download,
file upload, file delete, file rename
- Chrome: view/navigate directories & and view files

**IOS 9.1**

- FTP Client lite: works flawless

**Windows 10 mobile**

- Metro file manager: Works with file/directory view & navigate, file download,
file upload, file delete, file rename. Slow and chaotic sequence of FTP commands.
Many unneeded re-login attempts.

**Conclusion**: All dedicated ftp clients work fine, and most
of the file managers too.

## Trouble shooting
The only trouble observed so far was clients not releasing the connections. You may tell
by the value of `uftp.client_list`, which should be empty if no client is connected, or by issuing the command rstat in ftp, which shows the number of connected clients.
In that case you may restart the server with uftpd.restart(). If `uftd.client_busy`
is `True` when no client is connected, then restart the server with with
`uftpd.restart()`. If you want to see what happens at the server, you may set verbose to 2.
Just restart it with  `uftpd.restart(verbose = 1)`,  or set `uftpd.verbose_l = 1`, and
`uftpd.verbose_l = 0` to stop control messages again.

## Files
- uftpd.py: Server source file for ESP8266 and ESP32 from version='v1.9.3-575 on
- ftp.py: Simple version of the ftp server, which works in foreground. This
can be used with all Micorpython versions. It terminates when the client closes the
session. Only a single session is supported by this variant.
- README.md: This one
