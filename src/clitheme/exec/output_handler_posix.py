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
import stat
import fcntl
import signal
import struct
import copy
import re
import sqlite3
import time
import threading
import queue
from typing import Optional, List
from .._generator import db_interface
from .. import _globalvar, frontend
from . import _labeled_print

# spell-checker:ignore cbreak ICANON readsize splitarray ttyname RDWR preexec pgrp pids

fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="exec")
# https://docs.python.org/3/library/stdtypes.html#str.splitlines
newlines=(b'\n',b'\r',b'\r\n',b'\v',b'\f',b'\x1c',b'\x1d',b'\x1e',b'\x85') 

def _process_debug(lines: List[bytes], debug_mode: List[str], is_stderr: bool=False, matched: bool=False, failed: bool=False) -> List[bytes]:
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
            line=bytes(f"\x1b[0;1;{'31' if is_stderr else '32'}{';47' if matched else ''}{';37;41' if failed else ''}m"+('e' if is_stderr else 'o')+'\x1b[0;1m'+(">")+"\x1b[0m ",'utf-8')+line+b"\x1b[0m"
        final_lines.append(line)
    return final_lines

def handler_main(command: List[str], debug_mode: List[str]=[], subst: bool=True):
    do_subst=subst
    if do_subst==True: 
        try: db_interface.connect_db()
        except FileNotFoundError: pass
    stdout_fd, stdout_slave=pty.openpty()
    stderr_fd, stderr_slave=pty.openpty()
    readsize=io.DEFAULT_BUFFER_SIZE

    env=copy.copy(os.environ)
    # Prevent apps from using "less" or "more" as pager, as it won't work here
    env['PAGER']="cat"
    prev_attrs=None
    try: prev_attrs=termios.tcgetattr(sys.stdout)
    except termios.error: pass
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
        elif sig==signal.SIGTSTP: # suspend signal
            if os.tcgetpgrp(stdout_fd)!=process.pid: # e.g. A shell running another process
                os.write(stdout_fd, b'\x1a') # Send '^Z' character; don't suspend the entire shell
            else: 
                process.send_signal(signal.SIGSTOP) # Stop the process
                signal.signal(signal.SIGTSTP, signal.SIG_DFL) # Unset signal handler to prevent deadlock
                os.kill(main_pid, signal.SIGTSTP) # Suspend itself
        elif sig==signal.SIGINT:
            os.write(stdout_fd, b'\x03') # '^C' character
        elif sig==signal.SIGQUIT:
            os.write(stdout_fd, b'\x1c') # '^\' character
    try:
        # Detect if stdin is piped (e.g. cat file|clitheme-exec grep content)
        stdin_fd=stdout_slave
        if stat.S_ISFIFO(os.stat(sys.stdin.fileno()).st_mode):
            r,w=os.pipe()
            def pipe_forward():
                # Background thread to forward stdin to subprocess pipe
                nonlocal r,w
                while True:
                    select.select([sys.stdin], [], [])
                    d=os.read(sys.stdin.fileno(), readsize)
                    if d==b'': # stdin is closed
                        os.close(w); break
                    os.write(w,d)
            t=threading.Thread(target=pipe_forward, daemon=True)
            t.start()
            stdin_fd=r
        def child_init():
            # Must start new session or some programs might not work properly
            os.setsid()

            # Make controlling terminal so programs can access TTY properly
            # [Explicitly open the tty to make it become a controlling tty.]
            # --This code and above description are from the source code of pty.fork()--
            tmp_fd = os.open(os.ttyname(stdout_slave), os.O_RDWR)
            tmp_fd2 = os.open(os.ttyname(stderr_slave), os.O_RDWR)
            os.close(tmp_fd);os.close(tmp_fd2)
        process=subprocess.Popen(command, stdin=stdin_fd, stdout=stdout_slave, stderr=stdout_slave, env=env, preexec_fn=child_init)
    except:
        _labeled_print(fd.feof("command-fail-err", "Error: failed to run command: {msg}", msg=_globalvar.make_printable(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    else:
        handle_signals=[signal.SIGTSTP, signal.SIGCONT, signal.SIGINT, signal.SIGQUIT]
        for sig in handle_signals:
            signal.signal(sig, signal_handler)
    output_lines=queue.Queue() # (line_content, is_stderr, do_subst_operation)
    def get_terminal_size(): return fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH',0,0,0,0))
    last_terminal_size=struct.pack('HHHH',0,0,0,0) # placeholder
    # this mechanism prevents user input from being processed through substrules
    last_input_content=None
    last_tcgetpgrp=os.tcgetpgrp(stdout_fd)

    def handle_debug_pgrp(foreground_pid: int):
        nonlocal last_tcgetpgrp
        if "foreground" in debug_mode and foreground_pid!=last_tcgetpgrp:
            message=f"\x1b[1m! \x1b[{'32' if foreground_pid==process.pid else '31'}mForeground: \x1b[4m{'True' if foreground_pid==process.pid else 'False'} ({foreground_pid})\x1b[0m\n"
            os.write(sys.stdout.fileno(), bytes(message, 'utf-8'))
            last_tcgetpgrp=foreground_pid
    thread_exception_handled=False
    def handle_exception(exc: Optional[Exception]=None):
        nonlocal thread_exception_handled; thread_exception_handled=True
        if prev_attrs!=None: termios.tcsetattr(sys.stdout, termios.TCSADRAIN, prev_attrs) # restore previous attributes
        print("\x1b[0m\x1b[?1;1000;1001;1002;1003;1005;1006;1015;1016l\n\x1b[J", end='') # reset color, mouse reporting, and clear the rest of the screen
        _labeled_print(fd.reof("internal-error-err", "Error: an internal error has occurred while executing the command (execution halted):"))
        if exc!=None: raise exc
        else: raise

    thread_debug=0
    def thread_debug_handle(sig, frame):
        nonlocal thread_debug
        if sig==signal.SIGUSR1: thread_debug=1
        elif sig==signal.SIGUSR2: thread_debug=2
    signal.signal(signal.SIGUSR1, thread_debug_handle)
    signal.signal(signal.SIGUSR2, thread_debug_handle)
    def output_read_loop():
        nonlocal last_input_content, output_lines
        unfinished_output=None # (line,is_stderr,do_subst_operation,foreground_pid,initial_time)
        try:
            while True:
                # Testing thread exception handling
                nonlocal thread_debug
                if thread_debug==1: raise Exception
                elif thread_debug==2: break

                # Set a short timeout value if there are unfinished outputs
                # Else, wait longer to reduce CPU usage
                timeout=0.002 if unfinished_output!=None or last_input_content!=None else 0.5
                try: fds=select.select([stdout_fd, sys.stdin, stderr_fd], [], [], timeout)[0]
                except OSError: fds=select.select([stdout_fd, stderr_fd], [], [], timeout)[0]
                # Handle user input from stdin
                if sys.stdin in fds:
                    data=os.read(sys.stdin.fileno(), readsize)
                    # if input from last iteration did not end with newlines, append new content
                    if last_input_content!=None: last_input_content+=data
                    else: last_input_content=data
                    try: os.write(stdout_fd, data)
                    except OSError: pass # Handle input/output error that might occur after program terminates
                # Handle output from stdout and stderr
                output_handled=False
                def handle_output(is_stderr: bool):
                    nonlocal unfinished_output, output_lines, output_handled, last_input_content

                    data=os.read(stderr_fd if is_stderr else stdout_fd, readsize)
                    foreground_pid=os.tcgetpgrp(stdout_fd)
                    do_subst_operation=True
                    # check if the output is user input. if yes, skip
                    if last_input_content!=None:
                        input_match_expression: bytes=re.escape(last_input_content).replace(b'\x7f', rb"(\x08 \x08|\x08\x1b\[K)") # type: ignore
                        input_equals=b'^'+input_match_expression+b'$'
                        # print(last_input_content, data, re.search(input_equals, data)!=None) # DEBUG
                        if re.search(input_equals, data)!=None:
                            do_subst_operation=False
                        last_input_content=None
                    lines=data.splitlines(keepends=True)
                    unfinished_cr_lines=None
                    unfinished_output_time=time.perf_counter()
                    for x in range(len(lines)):
                        line=lines[x]
                        # if unfinished output exists, append new content to it
                        if x==0 and unfinished_output!=None:
                            orig_data=unfinished_output
                            orig_line=orig_data[0]
                            if unfinished_output[3]==foreground_pid and unfinished_output[1]==is_stderr and time.perf_counter()-unfinished_output[4]<=0.1:
                                # Modify existing line data instead of directly pushing it
                                # to better handle multiple fragments in a single line
                                line=orig_line+line
                                unfinished_output_time=unfinished_output[4]
                            else:
                                # Shouldn't join them together in this case
                                output_lines.put(unfinished_output)
                                # Don't push the current line just yet; leave it for newline check
                            unfinished_output=None
                            output_handled=True
                        if unfinished_cr_lines!=None: line=unfinished_cr_lines+line
                        # If line ends with carriage return ('\r') and is not end of content, process them together 
                        # to minimize visible cursor blinks due to delay in unfinished output processing
                        if line.endswith(b'\r') and x!=len(lines)-1:
                            unfinished_cr_lines=line
                            continue
                        else: unfinished_cr_lines=None
                        # if last line of output did not end with newlines, leave for next iteration
                        if x==len(lines)-1 and not line.endswith(newlines):
                            unfinished_output=(line,is_stderr,do_subst_operation, foreground_pid, unfinished_output_time)
                            output_handled=True
                        else:
                            last_index=0
                            for x in range(len(line)):
                                if line[x]==ord(b'\r') or x==len(line)-1:
                                    try:
                                        if line[x+1]==ord(b'\n'): continue
                                    except IndexError: pass
                                    output_lines.put((line[last_index:x+1], is_stderr, do_subst_operation, foreground_pid))
                                    last_index=x+1

                if stdout_fd in fds: handle_output(is_stderr=False)
                if stderr_fd in fds: handle_output(is_stderr=True)
                # if no unfinished_output is handled by handle_output, append the unfinished output if exists
                if not output_handled and unfinished_output!=None:
                    output_lines.put(unfinished_output)
                    unfinished_output=None
                # Reset last input content if no output is made within timeout
                if not sys.stdin in fds and last_input_content!=None:
                    last_input_content=None

                if process.poll()!=None: 
                    # Send termination signal
                    output_lines.put(None)
                    break
        except: handle_exception()
    
    thread=threading.Thread(target=output_read_loop, name="output-reader", daemon=True)
    thread.start()

    def update_window_size(*args):
        # update terminal size
        nonlocal last_terminal_size
        try:
            new_term_size=get_terminal_size()
            if new_term_size!=last_terminal_size:
                last_terminal_size=new_term_size
                fcntl.ioctl(stdout_fd, termios.TIOCSWINSZ, new_term_size)
                fcntl.ioctl(stderr_fd, termios.TIOCSWINSZ, new_term_size)
                process.send_signal(signal.SIGWINCH)
        except: pass
    signal.signal(signal.SIGWINCH, update_window_size)
    # Call this function for the first time to set initial window size
    update_window_size()
    while True:
        try:
            if not thread.is_alive() and not process.poll()!=None:
                if not thread_exception_handled: handle_exception(RuntimeError("Output read loop terminated unexpectedly"))
                else: return 1
            if thread_exception_handled: continue # Prevent conflict with setting terminal attributes
            # update terminal attributes from what the program sets
            try: 
                attrs=termios.tcgetattr(stdout_fd)
                # disable canonical and echo mode (enable cbreak) no matter what
                attrs[3] &= ~(termios.ICANON | termios.ECHO)
                termios.tcsetattr(sys.stdout, termios.TCSADRAIN, attrs)
            except termios.error: pass

            # Process outputs
            def process_line(line: bytes, line_data):
                nonlocal last_tcgetpgrp
                # subst operation
                subst_line=copy.copy(line)
                failed=False
                foreground_pid=line_data[3]
                # Print message if foreground process changed
                if line_data[2]==True: handle_debug_pgrp(foreground_pid)
                if do_subst and line_data[2]==True:
                    def operation():
                        nonlocal subst_line, failed, foreground_pid
                        try: 
                            subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1], pids=(process.pid, foreground_pid))
                        except TimeoutError: failed=True
                        # Happens when no theme is set/no subst-data.db
                        except sqlite3.OperationalError: pass
                    def raise_error(sig_num, frame): raise TimeoutError("Execution time out")
                    signal.signal(signal.SIGALRM, raise_error)
                    signal.setitimer(signal.ITIMER_REAL, db_interface.match_timeout)
                    operation()
                    # remove the interval timer to prevent exception when function finishes before timeout
                    signal.setitimer(signal.ITIMER_REAL, 0)
                if line_data[2]==True: subst_line=_process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line, failed=failed)[0] 
                return subst_line
            if output_lines.empty():
                handle_debug_pgrp(os.tcgetpgrp(stdout_fd))
            try: line_data=output_lines.get(block=True, timeout=0.5)
            except queue.Empty: continue
            # None: termination signal
            if line_data==None: break
            line: bytes=line_data[0]
            # subst operation and print output
            os.write(sys.stderr.fileno() if line_data[1]==True else sys.stdout.fileno(), process_line(line, line_data))
        except: 
            if not thread_exception_handled: handle_exception()
            else: raise
    if prev_attrs!=None: termios.tcsetattr(sys.stdout, termios.TCSADRAIN, prev_attrs) # restore previous attributes
    exit_code=process.poll()
    try:
        if exit_code!=None and exit_code<0: # Terminated by signal
            signal.signal(signal.SIGQUIT, signal.SIG_DFL) # Unset SIGQUIT custom handler
            os.kill(os.getpid(), abs(exit_code))
    except: pass
    return exit_code
