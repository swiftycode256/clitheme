# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Main output processing handler for Unix/Linux systems (internal module)
"""

import subprocess
import sys
import os
import io
import pty
import select
import termios
import fcntl
import signal
import struct
import copy
import re
import sqlite3
import concurrent.futures
from .._generator import db_interface
from .. import _globalvar, frontend
from . import _labeled_print

# spell-checker:ignore cbreak ICANON readsize splitarray ttyname RDWR preexec

_globalvar.handle_set_themedef(frontend, "output_handler_posix")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="exec")
# https://docs.python.org/3/library/stdtypes.html#str.splitlines
newlines=(b'\n',b'\r',b'\r\n',b'\v',b'\f',b'\x1c',b'\x1d',b'\x1e',b'\x85') 

def _process_debug(lines: list[bytes], debug_mode: list[str], is_stderr: bool=False, matched: bool=False, failed: bool=False) -> list[bytes]:
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
            line=bytes(f"\x1b[0;1;{'31' if is_stderr else '32'}{';47' if matched else ''}{';37;41' if failed else ''}m"+('e' if is_stderr else 'o')+'\x1b[0;1m'+(">")+"\x1b[0m ",'utf-8')+line+b"\x1b[0m"
        final_lines.append(line)
    return final_lines

def handler_main(command: list[str], debug_mode: list[str]=[], subst: bool=True):
    do_subst=subst
    if do_subst==True: 
        try: db_interface.connect_db()
        except FileNotFoundError: pass
    stdout_fd, stdout_slave=pty.openpty()
    stderr_fd, stderr_slave=pty.openpty()

    env=copy.copy(os.environ)
    # Prevent apps from using "less" or "more" as pager, as it won't work here
    env['PAGER']="cat"
    prev_attrs=termios.tcgetattr(sys.stdin)
    main_pid=os.getpid()
    process: subprocess.Popen
    # Redirect stderr to stdout for now (BETA)
        # need to find a method to preserve exact order when using separated stdout and stderr pipes
    
    # Since a new session is started with os.setsid() in child process:
    # - Suspend and continue signals must be manually relayed to the child process
    # [Not implemented yet] - Suspend signal from child process must be manually relayed to the parent process
    def signal_handler(sig, frame):
        if sig==signal.SIGCONT: # continue signal
            process.send_signal(sig)
            signal.signal(signal.SIGTSTP, signal_handler) # Reset signal handler
        if sig==signal.SIGTSTP: # suspend signal
            if os.tcgetpgrp(stdout_fd)!=process.pid: # e.g. A shell running another process
                os.write(stdout_fd, b'\x1a') # Send '^Z' character; don't suspend the entire shell
            else: 
                process.send_signal(signal.SIGSTOP) # Stop the process
                signal.signal(signal.SIGTSTP, signal.SIG_DFL) # Unset signal handler to prevent deadlock
                os.kill(main_pid, signal.SIGTSTP) # Suspend itself
    try:
        def child_init():
            # Must start new session or some programs might not work properly
            os.setsid()

            # Make controlling terminal so programs can access TTY properly
            # [Explicitly open the tty to make it become a controlling tty.]
            # --This code and above description are from the source code of pty.fork()--
            tmp_fd = os.open(os.ttyname(stdout_slave), os.O_RDWR)
            tmp_fd2 = os.open(os.ttyname(stderr_slave), os.O_RDWR)
            os.close(tmp_fd);os.close(tmp_fd2)
        process=subprocess.Popen(command, stdin=stdout_slave, stdout=stdout_slave, stderr=stdout_slave, bufsize=0, close_fds=True, env=env, preexec_fn=child_init)
    except:
        _labeled_print(fd.feof("command-fail-err", "Error: failed to run command: {msg}", msg=_globalvar.make_printable(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    else:
        signal.signal(signal.SIGTSTP, signal_handler)
        signal.signal(signal.SIGCONT, signal_handler)
    output_lines=[] # (line_content, is_stderr, do_subst_operation)
    def get_terminal_size(): return fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('HHHH',0,0,0,0))
    last_terminal_size=struct.pack('HHHH',0,0,0,0) # placeholder
    # this mechanism prevents user input from being processed through substrules
    last_input_content=None
    executor=concurrent.futures.ThreadPoolExecutor()
    last_tcgetpgrp=os.tcgetpgrp(stdout_fd)
    while True:
        try:
            # update terminal attributes from what the program sets
            try: 
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
            # Handle user input from stdin
            if sys.stdin in fds:
                data=os.read(sys.stdin.fileno(), readsize)
                # if input from last iteration did not end with newlines, append new content
                if last_input_content!=None: last_input_content+=data
                else: last_input_content=data
                os.write(stdout_fd, data)
            # Handle output from stdout and stderr
            def handle_output(is_stderr: bool):
                data=os.read(stderr_fd if is_stderr else stdout_fd, readsize)
                do_subst_operation=True
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

            # Print message if foreground process changed
            if "normal" in debug_mode:
                foreground_pid=os.tcgetpgrp(stdout_fd)
                if foreground_pid!=last_tcgetpgrp:
                    if (foreground_pid==process.pid)!=(last_tcgetpgrp==process.pid):
                        message=f"\x1b[1m! \x1b[{'32' if foreground_pid==process.pid else '31'}mForeground: \x1b[4m{'True' if foreground_pid==process.pid else 'False'}\x1b[0m\n"
                        os.write(sys.stdout.fileno(), bytes(message, 'utf-8'))
                    last_tcgetpgrp=foreground_pid

            # Process outputs
            def process_line(line: bytes, line_data):
                # subst operation
                subst_line=copy.copy(line)
                failed=False
                if do_subst and line_data[2]==True:
                    def operation():
                        nonlocal subst_line, failed
                        try: 
                            subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1], pids=(process.pid, os.tcgetpgrp(stdout_fd)))
                        except TimeoutError: failed=True
                        # Happens when no theme is set/no subst-data.db
                        except sqlite3.OperationalError: pass
                    if db_interface.enable_multiprocessing:
                        # First implementation (A): use the separate process in db_interface
                        # No additional actions required
                        operation()
                    else:
                        # Alternative implementation (B): use signal handlers to force exception in execution when catastrophic backtracking happens (timeout)
                        # --Multithreading cannot be used in implementation B--
                            # This means that only one line is processed at the same time; not ideal if multiple output lines are experiencing catastrophic backtracking
                        def raise_error(sig_num, frame): raise TimeoutError("Execution time out")
                        signal.signal(signal.SIGALRM, raise_error)
                        signal.setitimer(signal.ITIMER_REAL, db_interface.match_timeout)
                        operation()
                        # remove the interval timer to prevent exception when function finishes before timeout
                        signal.setitimer(signal.ITIMER_REAL, 0)
                if line_data[2]==True: subst_line=_process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line, failed=failed)[0] 
                return subst_line
            futures=[]
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
                if db_interface.enable_multiprocessing: futures.append(executor.submit(process_line, line, line_data))
                # print output
                else: os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), process_line(line, line_data))
            else: output_lines=[] # happens when no 'break' statement occurs
            # Print outputs (if enable_multiprocessing)
            for thread in futures:
                os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), thread.result())
        except KeyboardInterrupt:
            os.write(stdout_fd, b'\x03') # '^C' character
            # try: 
            #     try: os.kill(os.tcgetpgrp(stdout_fd), signal.SIGINT) # Send signal to foreground process
            #     except OSError: process.send_signal(signal.SIGINT)
            # except KeyboardInterrupt: pass
        except:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, prev_attrs) # restore previous attributes
            print("\x1b[0m\x1b[?1;1000;1001;1002;1003;1005;1006;1015;1016l", end='') # reset color and mouse reporting
            _labeled_print(fd.reof("internal-error-err", "Error: an internal error has occurred while executing the command (execution halted):"))
            raise
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, prev_attrs) # restore previous attributes
    return process.poll()
