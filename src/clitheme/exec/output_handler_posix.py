import subprocess
import sys
import os
import io
import pty, tty
import select
import termios
import fcntl
import signal
import struct
import copy
import re
from .._generator import db_interface
from .. import _globalvar, frontend
from . import _labeled_print

_globalvar.handle_set_themedef(frontend, "output_handler_posix")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="exec")
# https://docs.python.org/3/library/stdtypes.html#str.splitlines
newlines=(b'\n',b'\r',b'\r\n',b'\v',b'\f',b'\x1c',b'\x1d',b'\x1e',b'\x85') 

def _process_debug(lines: list[bytes], debug_mode: list[str], is_stderr: bool=False, matched: bool=False) -> list[bytes]:
    final_lines=[]
    for x in range(len(lines)):
        line=lines[x]
        if "showchars" in debug_mode:
            wrapper=b"\x1b[4;32m{}\x1b[0m"
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
            match_pattern=r"(^|\x1b\[[\d;]*?m)"
            sub_pattern=f"\\g<0>\x1b[{'31' if is_stderr else '33'}m"
            try: line=bytes(re.sub(match_pattern, sub_pattern, line.decode('utf-8')), 'utf-8')
            except UnicodeDecodeError: line=re.sub(bytes(match_pattern, 'utf-8'), bytes(sub_pattern, 'utf-8'), line)
            line+=b'\x1b[0m'
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

    env=copy.copy(os.environ)
    # Prevent apps from using "less" or "more" as pager, as it won't work here
    env['PAGER']="cat"
    process: subprocess.Popen
    # Redirect stderr to stdout for now (BETA)
        # need to find a method to preserve exact order when using separated stdout and stderr pipes
    try: process=subprocess.Popen(command, stdin=stdout_slave, stdout=stdout_slave, stderr=stdout_slave, bufsize=0, close_fds=True, env=env)
    except:
        _labeled_print(fd.feof("command-fail-err", "Error: failed to run command: {msg}", msg=str(sys.exc_info()[1])))
        return 1
    prev_attrs=termios.tcgetattr(sys.stdin)
    output_lines=[] # (line_content, is_stderr, do_subst_operation)
    def get_terminal_size(): return fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('HHHH',0,0,0,0))
    last_terminal_size=struct.pack('HHHH',0,0,0,0) # placeholder
    # this mechanism prevents user input from being processed through substrules
    last_input_content=None
    while True:
        try:
            # update terminal attributes from what the program sets
            try: 
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(stdout_fd))
                attrs=termios.tcgetattr(stdout_fd)
                # disable canonical and echo mode (enable cbreak) no matter what
                attrs[3] &= ~(termios.ICANON | termios.ECHO)
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attrs)
            except termios.error: pass
            # update terminal size
            try:
                new_term_size=get_terminal_size()
                if new_term_size!=last_terminal_size:
                    last_terminal_size=new_term_size
                    fcntl.ioctl(stdout_fd, termios.TIOCSWINSZ, new_term_size)
                    fcntl.ioctl(stderr_fd, termios.TIOCSWINSZ, new_term_size)
                    process.send_signal(signal.SIGWINCH)
            except: pass
            fds=select.select([stdout_fd, sys.stdin, stderr_fd], [], [], 0.01)[0]
            readsize=io.DEFAULT_BUFFER_SIZE
            if sys.stdin in fds:
                data=os.read(sys.stdin.fileno(), readsize)
                # if input from last iteration did not end with newlines, append new content
                if last_input_content!=None: last_input_content+=data
                else: last_input_content=data
                # if child process not in cbreak mode, output the characters
                # if termios.tcgetattr(stdin_fd)[3] & termios.ICANON:
                #     os.write(sys.stdout.fileno(), data)
                #     # output a new line if return key is pressed and ends on \r
                #     if data.endswith(b'\r'): os.write(sys.stdout.fileno(), b'\n')
                # if not data: break
                os.write(stdout_fd, data)
                # ^C pressed
                # if data==b'\x03' and (not termios.tcgetattr(stdout_fd)[0] & termios.IGNBRK) and termios.tcgetattr(stdout_fd)[0] & termios.BRKINT: process.send_signal(signal.SIGINT)
            def handle_output(is_stderr: bool):
                data=os.read(stderr_fd if is_stderr else stdout_fd, readsize)
                do_subst_operation=True
                # nonlocal last_input_content
                # print(last_input_content, data, data==last_input_content)
                # if data==last_input_content: do_subst_operation=False
                # last_input_content=None
                lines=data.splitlines(keepends=True)
                for x in range(len(lines)):
                    line=lines[x]
                    # if last input did not end with newlines, append new content to it
                    if x==0 and len(output_lines)>0 and not output_lines[-1][0].endswith(newlines):
                        orig_line=output_lines[-1][0]
                        output_lines.pop()
                        output_lines.append((orig_line+line,is_stderr,do_subst_operation))
                    else: output_lines.append((line,is_stderr,do_subst_operation))
            if stdout_fd in fds: handle_output(is_stderr=False)
            if stderr_fd in fds: handle_output(is_stderr=True)

            if process.poll()!=None and len(output_lines)==0: break
            # Process outputs
            for x in range(len(output_lines)):
                line_data=output_lines[x]
                line: bytes=line_data[0]
                # if does not end with newlines, leave it for the next iteration
                if x==len(output_lines)-1 and not line.endswith(newlines):
                    if not len(line_data)>=4: # not from previous iteration
                        output_lines=[line_data+(True,)] # add another entry to signal it's from previous iteration
                        break
                # check if the output is user input. if yes, skip
                # print(last_input_content, line) # DEBUG
                if line==last_input_content: line_data=(line_data[0],line_data[1],False); last_input_content=None
                elif last_input_content!=None and last_input_content.startswith(line): 
                    line_data=(line_data[0],line_data[1],False)
                    last_input_content=last_input_content[len(line):]
                else: last_input_content=None
                # subst operation
                subst_line=copy.copy(line)
                if do_subst and line_data[2]==True: subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1])
                if line_data[2]==True: subst_line=_process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line)[0] 
                os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), subst_line)
            else: output_lines=[] # happens when no 'break' statement occurs
        except KeyboardInterrupt:
            try: process.send_signal(signal.SIGINT)
            except KeyboardInterrupt: pass
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, prev_attrs) # restore previous attributes
    return process.poll()
