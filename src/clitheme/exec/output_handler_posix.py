import subprocess
import sys
import os
import io
import pty
import select
import termios
import copy
try:
    from .._generator import db_interface
    from .. import _globalvar, frontend
except ImportError:
    from _generator import db_interface
    import _globalvar, frontend

_globalvar.handle_set_themedef(frontend, "output_handler_posix")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="exec")
# https://docs.python.org/3/library/stdtypes.html#str.splitlines
newlines=(b'\n',b'\r',b'\r\n',b'\v',b'\f',b'\x1c',b'\x1d',b'\x1e',b'\x85') 

def _process_debug(lines: list[bytes], debug_mode: list[str], is_stderr: bool=False, matched: bool=False) -> list[bytes]:
    # debug_mode: newlines, showchars, color
    final_lines=[]
    for x in range(len(lines)):
        line=lines[x]
        if "showchars" in debug_mode:
            wrapper=b"\x1b[32m{}\x1b[0m"
            if "color" in debug_mode: wrapper+=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')
            line=line.replace(b'\x1b', wrapper.replace(b'{}', b'{{ESC}}')) # this must come before anything else
            line=line.replace(b'\r', wrapper.replace(b'{}',b'\\r'))
            line=line.replace(b'\n', wrapper.replace(b'{}',b'\\n')+b'\n')
            line=line.replace(b'\b', wrapper.replace(b'{}',b'\\x08'))
            line=line.replace(b'\a', wrapper.replace(b'{}',b'\\x07'))
        if "newlines" in debug_mode:
            if not line.endswith(b'\n'):
                line+=b"\n"
        if "color" in debug_mode:
            line=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')+line+b"\x1b[0m"
        if "normal" in debug_mode:
            # e.g. o{ <line>; o> <start>
            line=bytes(f"\x1b[0;1;{'31' if is_stderr else '32'}{';47' if matched else ''}m"+('e' if is_stderr else 'o')+'\x1b[0;1m'+(">")+"\x1b[0m ",'utf-8')+line+b"\x1b[0m"
        final_lines.append(line)
    return final_lines

def _handler_main(command: list[str], debug_mode: list[str]=[]):
    do_subst=True
    try: db_interface.connect_db()
    except FileNotFoundError: do_subst=False
    stdout_fd, stdout_slave=pty.openpty()
    stderr_fd, stderr_slave=pty.openpty()
    stdin_fd, stdin_slave=pty.openpty()

    env=copy.copy(os.environ)
    # Prevent apps from using "less" or "more" as pager, as it won't work here
    env['PAGER']="cat"
    process: subprocess.Popen
    # Redirect stderr to stdout for now (BETA)
        # need to find a method to preserve exact order when using separated stdout and stderr pipes
    try: process=subprocess.Popen(command, stdin=stdin_slave, stdout=stdout_slave, stderr=stdout_slave, bufsize=0, close_fds=True, env=env)
    except:
        print(fd.feof("command-fail-err", "Error: failed to run command: {msg}", msg=str(sys.exc_info()[1])))
        return 1
    output_lines=[] # (line_content, is_stderr)
    while True:
        try:
            # update cbreak (realtime stdin) attributes from what the program sets
            try: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(stdin_fd))
            except termios.error: pass
            fds=select.select([stdout_fd, sys.stdin, stderr_fd], [], [], 0.01)[0]
            readsize=io.DEFAULT_BUFFER_SIZE
            if sys.stdin in fds:
                data=os.read(sys.stdin.fileno(), readsize)
                if not data: break
                os.write(stdin_fd, data)
            if stdout_fd in fds:
                data=os.read(stdout_fd, readsize)
                #data=b'\x1b[33m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[33m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[33m'+data+b'\x1b[0m' # DEBUG purposes
                lines=data.splitlines(keepends=True)
                for x in range(len(lines)):
                    line=lines[x]
                    # if last input did not end with newlines, append new content to it
                    if x==0 and len(output_lines)>0 and not output_lines[-1][0].endswith(newlines):
                        orig_line=output_lines[-1][0]
                        output_lines.pop()
                        output_lines.append((orig_line+line,False))
                    else: output_lines.append((line,False))
            if stderr_fd in fds:
                data=os.read(stderr_fd, readsize)
                #data=b'\x1b[31m'+data.replace(b'\x1b',b'\x1b[32m{{ESC}}\x1b[31m')+b'\x1b[0m' # DEBUG purposes
                #data=b'\x1b[31m'+data+b'\x1b[0m' # DEBUG purposes
                lines=data.splitlines(keepends=True)
                for x in range(len(lines)):
                    line=lines[x]
                    if x==0 and len(output_lines)>0 and not output_lines[-1][0].endswith(newlines):
                        orig_line=output_lines[-1][0]
                        output_lines.pop()
                        output_lines.append((orig_line+line,True))
                    else: output_lines.append((line,True))
            if process.poll()!=None and len(output_lines)==0: break
            # Process outputs
            for x in range(len(output_lines)):
                line_data=output_lines[x]
                line: bytes=line_data[0]
                # if does not end with newlines, leave it for the next iteration
                if x==len(output_lines)-1 and not line.endswith(newlines):
                    if not len(line_data)>2: # not from previous iteration
                        output_lines=[line_data+(True,)] # add another entry to signal it's from previous iteration
                        break
                # subst operation
                subst_line=copy.copy(line)
                if do_subst: subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1])
                subst_line=_process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line)[0] 
                os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), subst_line)
            else: output_lines=[] # happens when no 'break' statement occurs
        except KeyboardInterrupt:
            try: process.send_signal(2) #SIGINT
            except KeyboardInterrupt: pass
            #os.write(stdin_fd, b'\x03')
    return process.poll()
