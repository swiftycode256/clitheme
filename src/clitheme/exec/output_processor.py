# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Main output processing handler for Unix/Linux systems (internal module)
"""

import sys
import os
import signal
import copy
import re
import time
import threading
import queue
from typing import Optional, List
from .._generator import db_interface
from .. import _globalvar, frontend
from .handlers._base_template import BaseHandler
from .._globalvar import _direct_exit
from . import _labeled_print

# spell-checker:ignore cbreak ICANON readsize splitarray ttyname RDWR preexec pgrp pids

fd=frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="exec")
# https://docs.python.org/3/library/stdtypes.html#str.splitlines

def _process_debug(lines: List[bytes], debug_mode: List[str], is_stderr: bool=False, matched: bool=False, failed: bool=False, do_subst: bool=False) -> List[bytes]:
    final_lines=[]
    for x in range(len(lines)):
        line=lines[x]
        if do_subst and "showchars" in debug_mode:
            wrapper=b"\x1b[4;32m{}\x1b[0m"
            if "color" in debug_mode: wrapper+=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')
            line=line.replace(b'\x1b', wrapper.replace(b'{}', b'{{ESC}}')) # this must come before anything else
            line=re.sub(rb'\r(?!\n)', wrapper.replace(b'{}',rb'\\r'), line)
            line=re.sub(rb'(?<!\r)\n', wrapper.replace(b'{}',rb'\\n')+b'\n', line)
            line=line.replace(b'\r\n', wrapper.replace(b'{}',rb'\r\n')+b'\r\n')
            line=line.replace(b'\b', wrapper.replace(b'{}',rb'\x08'))
            line=line.replace(b'\a', wrapper.replace(b'{}',rb'\x07'))
        if do_subst and "newlines" in debug_mode:
            if not line.endswith(b'\n'):
                line+=b"\n"
        if "color" in debug_mode:
            match_pattern=r"(^|\x1b\[[\d;]*?m)"
            if do_subst:
                sub_pattern=f"\\g<0>\x1b[{'31' if is_stderr else '33'}m" # Yellow or Red
            else:
                sub_pattern=f"\\g<0>\x1b[38;5;8m" # Gray
            try: line=bytes(re.sub(match_pattern, sub_pattern, line.decode('utf-8')), 'utf-8')
            except UnicodeDecodeError: line=re.sub(bytes(match_pattern, 'utf-8'), bytes(sub_pattern, 'utf-8'), line)
            line+=b'\x1b[0m'
        if do_subst and "normal" in debug_mode:
            line=bytes(f"\x1b[0;1;{'31' if is_stderr else '32'}{';47' if matched else ''}{';37;41' if failed else ''}m"+('e' if is_stderr else 'o')+'\x1b[0;1m'+(">")+"\x1b[0m ",'utf-8')+line+b"\x1b[0m"
        final_lines.append(line)
    return final_lines

def handler_main(command: List[str], debug_mode: List[str]=[], subst: bool=True):
    do_subst=subst
    if do_subst==True: 
        try: db_interface.connect_db()
        except FileNotFoundError: pass
    
    try:
        handler: BaseHandler
        if os.name=="posix":
            from .handlers.posix import PosixHandler
            handler=PosixHandler(command)
        else: 
            from .handlers.windows import WindowsHandler
            handler=WindowsHandler(command)
    except:
        _labeled_print(fd.feof("command-fail-err", "Error: failed to run command: {msg}", msg=_globalvar.make_printable(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    output_lines=queue.Queue() # (line_content, is_stderr, do_subst_operation, foreground_pid, term_attrs)
    last_tcgetpgrp=handler.get_foreground_pid()

    def handle_debug_pgrp(foreground_pid: Optional[int]):
        nonlocal handler, last_tcgetpgrp
        if "foreground" in debug_mode and foreground_pid!=last_tcgetpgrp:
            message=f"\x1b[1m! \x1b[{'32' if foreground_pid==handler.process_pid else '31'}mForeground: \x1b[4m{'True' if foreground_pid==handler.process_pid else 'False'} ({foreground_pid})\x1b[0m\n"
            handler.write_output(bytes(message, 'utf-8'))
            last_tcgetpgrp=foreground_pid
    thread_exception_handled=False
    def handle_exception(exc: Optional[Exception]=None):
        nonlocal thread_exception_handled; thread_exception_handled=True
        handler.reset_terminal()
        _labeled_print(fd.reof("internal-error-err", "Error: an internal error has occurred while executing the command (execution halted):"))
        if exc!=None: raise exc
        else: raise

    thread_debug=0
    if os.name=="posix":
        def thread_debug_handle(sig, frame):
            nonlocal thread_debug
            if sig==signal.SIGUSR1: thread_debug=1
            elif sig==signal.SIGUSR2: thread_debug=2
        signal.signal(signal.SIGUSR1, thread_debug_handle)
        signal.signal(signal.SIGUSR2, thread_debug_handle)
    def output_read_loop():
        nonlocal output_lines
        unfinished_output=None # (line,is_stderr,do_subst_operation,foreground_pid,term_attrs,initial_time)
        # Just in case where input is read in multiple segments before output arrives
        last_input_content=None
        def push_output(content):
            nonlocal unfinished_output, last_input_content
            unfinished_output=None; last_input_content=None
            output_lines.put(content)
        try:
            while True:
                time.sleep(0.001)
                # Testing thread exception handling
                nonlocal thread_debug
                if thread_debug==1: raise Exception
                elif thread_debug==2: break

                # Set a short timeout value if there are unfinished outputs
                # Else, wait longer to reduce CPU usage
                timeout=0.005 if unfinished_output!=None or last_input_content!=None else 0.1
                fds=handler.get_readable_descriptors(timeout)
                # Handle user input from stdin
                if "stdin" in fds:
                    data=handler.read_stdin()
                    # if input from last iteration did not end with newlines, append new content
                    if last_input_content!=None: last_input_content+=data
                    else: last_input_content=data
                    try: handler.write_pty(data)
                    except OSError: pass # Handle input/output error that might occur after program terminates
                # Handle output from stdout and stderr
                def handle_output(is_stderr: bool) -> bool:
                    nonlocal unfinished_output, output_lines, last_input_content

                    term_attrs=handler.get_process_term_attrs(no_buffering=True)
                    foreground_pid=handler.get_foreground_pid()
                    data=handler.read_pty(is_stderr=is_stderr)
                    # If pipe closed and returns empty data, ignore
                    if data==b'': return False

                    unfinished_output_time=time.perf_counter()
                    if unfinished_output!=None:
                        orig_data=unfinished_output[0]
                        if unfinished_output[3]==foreground_pid and unfinished_output[1]==is_stderr:
                            # If exceeds maximum time or differing terminal attributes, append first line of data into unfinished output and process it
                            if time.perf_counter()-unfinished_output[5]>0.05 or term_attrs!=unfinished_output[4]:
                                lines=data.splitlines(keepends=True)
                                push_output((unfinished_output[0]+lines[0],)+unfinished_output[1:])
                                data=data[len(lines[0]):] # Remove first line from data
                            else:
                                # Modify existing line data instead of directly pushing it
                                # to better handle multiple fragments in a single line
                                data=orig_data+data
                                unfinished_output_time=unfinished_output[5]
                        else:
                            # Shouldn't join them together in this case
                            push_output(unfinished_output)
                            # Don't push the current line just yet; leave it for newline check
                    # If all data was appended to previous unfinished output and pushed, don't do anything
                    if data==b'': return True
                    # Check if the output is user input
                    do_subst_operation=True
                    if last_input_content!=None:
                        # Windows keystroke input: "\x1b[0;0;0;0;0;0_"
                        windows_input_expr=rb"\x1b\[\d+?;\d+?;(?P<char>\d+?);(?P<pressed>\d+?);\d+?;\d+?_"
                        if re.fullmatch(b'('+windows_input_expr+b')+', last_input_content)!=None:
                            # Process input sequence: Discard parts with char=0
                            target_input=b''
                            remaining=last_input_content
                            while len(remaining)>0:
                                match_obj=re.match(b'^'+windows_input_expr, remaining)
                                assert match_obj!=None, "Failed to match Windows keystroke input"
                                if int(match_obj.groupdict()['char'])!=0:
                                    target_input+=match_obj.group(0)
                                remaining=remaining[len(match_obj.group(0)):]
                            # Construct output match pattern
                            target_output=b''
                            for char_code in re.sub(rb"(\x08 \x08|\x08\x1b\[K)", b'\x08', data):
                                for pressed in (b'1',b'0'):
                                    target_output+=rb"\x1b\[\d+?;\d+?;"+str(char_code).encode()+rb";"+pressed+rb";\d+?;\d+?_"
                            # print(target_input, target_output, re.fullmatch(target_output, target_input)!=None) # DEBUG
                            if re.fullmatch(target_output, target_input)!=None: do_subst_operation=False
                        else:
                            # Unix keystroke: mostly same as output
                            input_match_expression: bytes=re.escape(last_input_content).replace(b'\x7f', rb"(\x08 \x08|\x08\x1b\[K)") # type: ignore
                            input_equals=b'^'+input_match_expression+b'$'
                            # print(last_input_content, data, re.search(input_equals, data)!=None) # DEBUG
                            if re.search(input_equals, data)!=None:
                                do_subst_operation=False
                    # if last line of output did not end with newlines, leave for next iteration
                    if not data.endswith(_globalvar.newlines):
                        unfinished_output=(data,is_stderr,do_subst_operation, foreground_pid, term_attrs, unfinished_output_time)
                    else: push_output((data, is_stderr, do_subst_operation, foreground_pid, term_attrs))
                    return True
                had_output=False
                if "stdout" in fds:
                    had_output=had_output or handle_output(is_stderr=False)
                if "stderr" in fds:
                    had_output=had_output or handle_output(is_stderr=True)
                # if no unfinished_output is handled by handle_output, append the unfinished output if exists
                if not had_output and unfinished_output!=None:
                    push_output(unfinished_output)
                    unfinished_output=None
                # Reset last input content if no output is made within timeout
                if not "stdin" in fds and unfinished_output==None:
                    last_input_content=None
                # End loop if process terminated and no output available for this round
                if handler.get_proc_status()!=None \
                    and had_output==False and unfinished_output==None: 
                    # Send termination signal
                    push_output(None)
                    break
        except: handle_exception()
    
    thread=threading.Thread(target=output_read_loop, name="output-reader", daemon=True)
    thread.start()

    # If had output on the previous run, use shorter timeout to minimize delay in --foreground-stat output
    had_output=False
    while True:
        try:
            if not thread.is_alive() and not handler.get_proc_status()!=None:
                if not thread_exception_handled: handle_exception(RuntimeError("Output read loop terminated unexpectedly"))
                else: return 1
            if thread_exception_handled: break # Prevent conflict with setting terminal attributes

            # Process outputs
            def process_line(line: bytes, line_data):
                nonlocal last_tcgetpgrp
                # subst operation
                subst_line=copy.copy(line)
                failed=False
                foreground_pid=line_data[3]
                if do_subst and line_data[2]==True:
                    if os.name=="posix":
                        def raise_error(sig_num, frame): raise TimeoutError("Execution time out")
                        signal.signal(signal.SIGALRM, raise_error)
                        signal.setitimer(signal.ITIMER_REAL, db_interface.match_timeout)
                    try: 
                        subst_line=db_interface.match_content(line, _globalvar.splitarray_to_string(command), is_stderr=line_data[1], pids=(handler.process_pid, foreground_pid))
                    except TimeoutError: failed=True
                    # Happens when no theme is set/no subst-data.db
                    except db_interface.db_not_found: pass
                    # remove the interval timer to prevent exception when function finishes before timeout
                    if os.name=="posix": signal.setitimer(signal.ITIMER_REAL, 0)
                subst_line=_process_debug([subst_line], debug_mode, is_stderr=line_data[1], matched=not subst_line==line, failed=failed, do_subst=line_data[2])[0] 
                return subst_line
            if output_lines.empty():
                handle_debug_pgrp(handler.get_foreground_pid())
            try: line_data=output_lines.get(block=True, timeout=0.05 if had_output else 0.1)
            except queue.Empty: 
                had_output=False
                continue
            # --Output processing--
            had_output=True
            # None: termination signal
            if line_data==None: break
            # Process output line by line
            output=b''
            for line in line_data[0].splitlines(keepends=True):
                output+=process_line(line, line_data)
            # Print message if foreground process changed and not user input
            if line_data[2]==True: handle_debug_pgrp(line_data[3])
            # update terminal attributes from what the program sets
            if line_data[4]!=None: handler.set_host_term_attrs(line_data[4])
            # subst operation and print output
            handler.write_output(output, is_stderr=line_data[1])
        except _direct_exit: break
        except: 
            if not thread_exception_handled: handle_exception()
            else: raise # Handle "output read loop terminated expectedly" without re-printing the message
    return handler.handle_exit()
