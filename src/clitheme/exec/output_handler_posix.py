import subprocess
import sys
import os
import pty
import select
import termios, tty
import time
import copy
try:
    from .._generator import db_interface
    from .. import _globalvar
except ImportError:
    from _generator import db_interface
    import _globalvar


def handler_main(command: list[str]):
    db_interface.connect_db()
    stdout_fd, stdout_slave=pty.openpty()
    stderr_fd, stderr_slave=pty.openpty()
    stdin_fd, stdin_slave=pty.openpty()

    env=copy.copy(os.environ)
    process=subprocess.Popen(command, stdin=stdin_slave, stdout=stdout_slave, stderr=stderr_slave, bufsize=0, close_fds=True, env=env)
    while process.poll()==None:
        try:
            # update cbreak (realtime stdin) attributes from what the program sets
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(stdin_fd))
            fds=select.select([stdout_fd, sys.stdin, stderr_fd], [], [], 0.1)[0]
            output_lines=[] # (line_content, is_stderr)
            if sys.stdin in fds:
                data=os.read(sys.stdin.fileno(), 1024)
                if not data: break
                os.write(stdin_fd, data)
            if stdout_fd in fds:
                data=os.read(stdout_fd, 1024)
                #data=b'\x1b[33m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[33m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[33m'+data+b'\x1b[0m' # DEBUG purposes
                for line in data.splitlines():
                    output_lines.append((line,False))
            if stderr_fd in fds:
                data=os.read(stderr_fd, 1024)
                #data=b'\x1b[31m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[31m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[31m'+data+b'\x1b[0m' # DEBUG purposes
                for line in data.splitlines():
                    output_lines.append((line,True))
            # Process outputs
            for line_data in output_lines:
                line=line_data[0]
                # subst operation
                subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1])
                os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), subst_line+b"\n")
        except KeyboardInterrupt:
            process.send_signal(2) #SIGINT
            #os.write(stdin_fd, b'\x03')
