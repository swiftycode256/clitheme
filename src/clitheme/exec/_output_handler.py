# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Main output processing handler (internal module)
"""

import os
import signal
import re
import time
import threading
import queue
from typing import Optional, List, Set
from .._generator import db_interface
from .. import _globalvar, frontend
from . import _substrules_processor
from ._handlers._base_template import BaseHandler, command_failed
from .._globalvar import _direct_exit, make_printable as fmt
from . import _labeled_print

# spell-checker:ignore cbreak ICANON readsize splitarray ttyname RDWR preexec pgrp pids

fd=frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="exec")

def _process_debug(lines: List[bytes], debug_mode: List[str], is_stderr: bool, matched_lines: Set[int], failed: bool, do_subst: bool) -> bytes:
    final_output=b''
    for x in range(len(lines)):
        line=lines[x]
        if do_subst and "showchars" in debug_mode:
            wrapper=b"\x1b[4;32m{}\x1b[0m"
            if "color" in debug_mode: wrapper+=bytes(f"\x1b[{'31' if is_stderr else '33'}m", 'utf-8')
            line=line.replace(b'\x1b', wrapper.replace(b'{}', b'{{ESC}}')) # this must come before anything else
            line=re.sub(rb'\r(?!\n)', wrapper.replace(b'{}',rb'\\r'), line)
            line=re.sub(rb'(?<!\r)\n', wrapper.replace(b'{}',rb'\\n')+b'\n', line)
            for c in (r'\r\n', r'\v', r'\f', r'\x1c', r'\x1d', r'\x1e'):
                line=line.replace(eval(f"b'{c}'"), wrapper.replace(b'{}', c.encode('utf-8'))+eval(f"b'{c}'"))
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
            line=bytes(f"\x1b[0;1;" # Bold
                       f"{'31' if is_stderr else '32'}" # Red/green
                       f"{';47;30' if x==0 else ''}" # White highlighting
                       f"{';44' if x in matched_lines else ''}" # Blue highlighting
                       f"{';37;41' if failed else ''}" # Red highlighting
                       'm'
                       f"{'e' if is_stderr else 'o'}"

                       f"\x1b[0;1;"
                       f"{';47;30' if x==0 else ''}"
                       'm'
                       f"{'>' if x==0 else '['}\x1b[0m ",
                       'utf-8')+line
        final_output+=line
    return final_output

def handler_main(command: List[str], debug_mode: List[str]=[], subst: bool=True):
    do_subst=subst
    if do_subst==True: 
        try: db_interface.connect_db()
        except db_interface.db_not_found: pass
    
    try:
        handler: BaseHandler
        if os.name=="posix":
            from ._handlers.posix import PosixHandler
            handler=PosixHandler(command)
        else: 
            from ._handlers.windows import WindowsHandler
            handler=WindowsHandler(command)
    except Exception as exc:
        if type(exc)==command_failed:
            _labeled_print(fd.feof("command-fail-err", "Failed to run command: {msg}", msg=fmt(str(exc))))
            _globalvar.handle_exception()
        else:
            _labeled_print(fd.feof("init-fail-err", "Initialization failed: {msg}", msg=fmt(str(exc))))
            raise # Always show full traceback
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
        _labeled_print(fd.reof("internal-error-err", "An internal error has occurred (process terminated):"))
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
        pending_output=None # (line,is_stderr,do_subst_operation,foreground_pid,term_attrs,initial_time)
        # Just in case where input is read in multiple segments before output arrives
        last_input_content=None
        def push_output(content):
            nonlocal pending_output, last_input_content
            pending_output=None; last_input_content=None
            output_lines.put(content)
        try:
            while True:
                time.sleep(0.001)
                # Testing thread exception handling
                nonlocal thread_debug
                if thread_debug==1: raise Exception
                elif thread_debug==2: break

                if last_input_content!=None: 
                    # Shorter timeout for inputs to reduce lag
                    timeout=0.005
                elif pending_output!=None:
                    # Short timeout if there are pending outputs
                    timeout=0.02
                else:
                    # Wait longer to reduce CPU usage
                    timeout=0.1
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
                    nonlocal pending_output, output_lines, last_input_content

                    term_attrs=handler.get_process_term_attrs(no_buffering=True)
                    foreground_pid=handler.get_foreground_pid()
                    data=handler.read_pty(is_stderr=is_stderr)
                    # If pipe closed and returns empty data, ignore
                    if data==b'': return False

                    pending_output_time=time.perf_counter()
                    if pending_output!=None:
                        orig_data=pending_output[0]
                        if pending_output[3]==foreground_pid and pending_output[1]==is_stderr:
                            # If exceeds maximum time or differing terminal attributes
                            if time.perf_counter()-pending_output[5]>0.1 or term_attrs!=pending_output[4]:
                                if not orig_data.endswith(_globalvar.newlines):
                                    # Append first line of data into pending output and process it
                                    first_line=re.match(_globalvar.line_match_bytes, data).group() # type: ignore
                                    push_output((orig_data+first_line,)+pending_output[1:])
                                    data=data[len(first_line):] # Remove first line from data
                                else: 
                                    # Don't need to join lines together
                                    push_output(pending_output)
                            else:
                                # Modify existing line data instead of directly pushing it
                                # to better handle multiple fragments in a single line
                                data=orig_data+data
                                pending_output_time=pending_output[5]
                        else:
                            # Shouldn't join them together in this case
                            push_output(pending_output)
                            # Don't push the current line just yet; leave it for newline check
                    # If all data was pushed, don't do anything
                    if data==b'': return True
                    # region: Check if the output is user input
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
                    # endregion
                    
                    # Update pending output
                    pending_output=(data,is_stderr,do_subst_operation, foreground_pid, term_attrs, pending_output_time)
                    return True
                had_output=False
                if "stdout" in fds:
                    had_output=had_output or handle_output(is_stderr=False)
                if "stderr" in fds:
                    had_output=had_output or handle_output(is_stderr=True)
                no_io_available=not "stdin" in fds and not had_output
                # if no input and output available, push what we have right now
                if no_io_available and pending_output!=None:
                    push_output(pending_output)
                    pending_output=None
                # Reset last input content if no output is made within timeout
                if not "stdin" in fds and pending_output==None:
                    last_input_content=None
                # End loop if process terminated and no input/output available for this round
                if handler.get_proc_status()!=None \
                    and no_io_available and pending_output==None: 
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
            if output_lines.empty():
                handle_debug_pgrp(handler.get_foreground_pid())
            try: block_data=output_lines.get(block=True, timeout=0.05 if had_output else 0.1)
            except queue.Empty: 
                had_output=False
                continue
            # --Output processing--
            had_output=True
            # None: termination signal
            if block_data==None: break
            # Process output line by line
            output=b''
            # subst operation
            new_output=block_data[0]
            changed_lines=set()
            failed=False
            foreground_pid=block_data[3]
            if do_subst and block_data[2]==True:
                if os.name=="posix":
                    def raise_error(sig_num, frame): raise TimeoutError("Execution time out")
                    signal.signal(signal.SIGALRM, raise_error)
                    signal.setitimer(signal.ITIMER_REAL, _globalvar.output_subst_timeout)
                try: 
                    new_output, changed_lines=_substrules_processor.match_content(new_output, ' '.join(command), is_stderr=block_data[1], pids=(handler.process_pid, foreground_pid))
                except TimeoutError: failed=True
                # Happens when no theme is set/no subst-data.db
                except db_interface.db_not_found: pass
                # remove the interval timer to prevent exception when function finishes before timeout
                if os.name=="posix": signal.setitimer(signal.ITIMER_REAL, 0)
            new_output=_process_debug([m.group() for m in re.finditer(_globalvar.line_match_bytes, new_output)][:-1], debug_mode, is_stderr=block_data[1], matched_lines=changed_lines, failed=failed, do_subst=block_data[2])
            output+=new_output
            # Print message if foreground process changed and not user input
            if block_data[2]==True: handle_debug_pgrp(block_data[3])
            # update terminal attributes from what the program sets
            if block_data[4]!=None: handler.set_host_term_attrs(block_data[4])
            # subst operation and print output
            handler.write_output(output, is_stderr=block_data[1])
        except _direct_exit: break
        except: 
            if not thread_exception_handled: handle_exception()
            else: raise # Handle "output read loop terminated expectedly" without re-printing the message
    return handler.handle_exit()
