import subprocess
import sys
import os
import pty
import select
import termios
import copy
import string
from typing import Optional
try:
    from .._generator import db_interface
    from .. import _globalvar
except ImportError:
    from _generator import db_interface
    import _globalvar


def process_debug(lines: list[bytes], debug_mode: list[str], is_stderr: bool=False, matched: bool=False) -> list[bytes]:
    # debug_mode: newlines, showchars, color
    final_lines=[]
    for x in range(len(lines)):
        line=lines[x]
        if "newlines" in debug_mode:
            if not line.endswith(b'\n') and not line.endswith(b'\f') and not line.endswith(b'\x0c'):
                line+=b"\n"
        if "showchars" in debug_mode:
            wrapper=b"\x1b[32m{}\x1b[0m"
            if "color" in debug_mode: wrapper+=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')
            line=line.replace(b'\x1b', wrapper.replace(b'{}', b'{{ESC}}')) # this must come before anything else
            line=line.replace(b'\r', wrapper.replace(b'{}',b'\\r'))
            line=line.replace(b'\b', wrapper.replace(b'{}',b'\\x08'))
            line=line.replace(b'\a', wrapper.replace(b'{}',b'\\x07'))
        if "color" in debug_mode:
            line=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')+line+b"\x1b[0m"
        if "normal" in debug_mode:
            # e.g. o{ <line>; o> <start>
            line=bytes(f"\x1b[0;1;{'31' if is_stderr else '32'}{';47' if matched else ''}m"+('e' if is_stderr else 'o')+'\x1b[0;1m'+(">")+"\x1b[0m ",'utf-8')+line+b"\x1b[0m"
        final_lines.append(line)
    return final_lines

def handler_main(command: list[str], debug_mode: list[str]=[]):
    do_subst=True
    try: db_interface.connect_db()
    except FileNotFoundError: do_subst=False
    stdout_fd, stdout_slave=pty.openpty()
    stderr_fd, stderr_slave=pty.openpty()
    stdin_fd, stdin_slave=pty.openpty()

    env=copy.copy(os.environ)
    # Tell apps that the terminal aren't designed to handle TUI
    env['TERM']="dumb"
    # Prevent apps from using "less" or "more" as pager, as it won't work here
    env['PAGER']="cat"
    process=subprocess.Popen(command, stdin=stdin_slave, stdout=stdout_slave, stderr=stderr_slave, bufsize=0, close_fds=True, env=env)
    while process.poll()==None:
        try:
            # update cbreak (realtime stdin) attributes from what the program sets
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(stdin_fd))
            fds=select.select([stdout_fd, sys.stdin, stderr_fd], [], [], 0.1)[0]
            output_lines=[] # (line_content, is_stderr)
            readsize=1000000
            if sys.stdin in fds:
                data=os.read(sys.stdin.fileno(), readsize)
                if not data: break
                os.write(stdin_fd, data)
            if stdout_fd in fds:
                data=os.read(stdout_fd, readsize)
                #data=b'\x1b[33m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[33m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[33m'+data+b'\x1b[0m' # DEBUG purposes
                lines=data.splitlines(keepends=True)
                for line in lines:
                    output_lines.append((line,False))
            if stderr_fd in fds:
                data=os.read(stderr_fd, readsize)
                #data=b'\x1b[31m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[31m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[31m'+data+b'\x1b[0m' # DEBUG purposes
                lines=data.splitlines(keepends=True)
                for line in lines:
                    output_lines.append((line,True))
            # Process outputs
            for line_data in output_lines:
                line=line_data[0]
                # subst operation
                subst_line=copy.copy(line)
                if do_subst: subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1])
                subst_line=process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line)[0] 
                os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), subst_line)
        except KeyboardInterrupt:
            process.send_signal(2) #SIGINT
            #os.write(stdin_fd, b'\x03')
