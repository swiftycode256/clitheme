# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import signal
import re
import time
import threading
import queue
from typing import Optional, List, Set
from .. import _globalvar, _frontend_internal as frontend
from . import _substrules_processor
from ._handlers._base_template import BaseHandler, command_failed
from .._globalvar import direct_exit, make_printable as fmt
from . import _labeled_print

# spell-checker:ignore pgrp pids

fd=frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="exec")

def _process_debug(lines: List[bytes], debug_mode: List[str], is_stderr: bool, matched_lines: Set[int], failed: bool, do_subst: bool) -> bytes:
    final_output=b''
    for x in range(len(lines)):
        line=lines[x]
        wrapper=b"\x1b[4;32m{}\x1b[0m"
        if do_subst and "showchars" in debug_mode:
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
                line+=b"\r\n"
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
            split_lines: List[bytes]=[]
            if "showchars" in debug_mode:
                # Further split lines by cursor positioning sequence (e.g. \x1b[5;1H)
                total_len=0
                seq=re.escape(wrapper.replace(b'{}', b'{{ESC}}'))
                for match in re.finditer(rb"(.+?)("+seq+rb"\[\d+;\d+H|\Z)", line, flags=re.DOTALL):
                    split_lines.append(match.group(0))
                    total_len+=len(match.group(0))
                assert total_len==len(line), f"Length mismatch: {total_len}!={len(line)}"
            else: split_lines.append(line)
            assert len(split_lines)>0, "Empty split_lines array"
            final_line=bytes(
                f"\x1b[0;1" # Bold
                f"{';31' if is_stderr else ';32'}" # Red/green
                f"{';30;47' if x==0 else ''}" # black on [white]
                f"{';37;44' if x in matched_lines else ''}" # white on [blue]
                f"{';37;41' if failed else ''}" # white on [red]
                'm'
                f"{'e' if is_stderr else 'o'}"

                f"\x1b[0;1" # Bold
                f"{';47;30' if x==0 else ''}" # black on [white]
                'm'
                f"{'>' if x==0 else '['}\x1b[0m ",
            'utf-8')+split_lines[0]
            for i in range(1,len(split_lines)):
                final_line+=b'\r\n'+b'\x1b[0;1m'+b' ( '+b'\x1b[0m'+\
                    split_lines[i]
            line=final_line
        final_output+=line
    return final_output

def handler_main(command: List[str], debug_mode: List[str]=[], subst: bool=True):
    do_subst=subst
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
            _globalvar.handle_exception(always_show=True)
        return 1
    output_lines=queue.Queue() # (line_content, is_stderr, do_subst_operation, foreground_pid, term_attrs)
    last_tcgetpgrp=handler.get_foreground_pid()

    def handle_debug_pgrp(foreground_pid: Optional[int]):
        nonlocal handler, last_tcgetpgrp
        if "foreground" in debug_mode and foreground_pid!=last_tcgetpgrp:
            message=f"\x1b[1m! \x1b[{'32' if foreground_pid==handler.process_pid else '31'}mForeground: \x1b[4m{'True' if foreground_pid==handler.process_pid else 'False'} ({foreground_pid})\x1b[0m\r\n"
            handler.write_output(bytes(message, 'utf-8'))
            last_tcgetpgrp=foreground_pid
    thread_exception_handled=False
    def handle_exception():
        nonlocal thread_exception_handled; thread_exception_handled=True
        handler.reset_terminal()
        _labeled_print(fd.reof("internal-error-err", "An internal error has occurred (process terminated):"))
        _globalvar.handle_exception(always_show=True)

    thread_debug=0
    if os.name=="posix":
        def thread_debug_handle(sig, frame):
            nonlocal thread_debug
            if sig==signal.SIGUSR1: thread_debug=1
            elif sig==signal.SIGUSR2: thread_debug=2
        signal.signal(signal.SIGUSR1, thread_debug_handle)
        signal.signal(signal.SIGUSR2, thread_debug_handle)
    def output_read_loop():
        pending_output=None # (line,is_stderr,do_subst_operation,foreground_pid,term_attrs,initial_time, line for comparing)
        # Just in case where input is read in multiple segments before output arrives
        last_input_content=None
        last_output_time=time.perf_counter()
        def push_output(content):
            nonlocal pending_output, last_input_content, last_output_time, output_lines
            if content!=None and last_input_content!=None \
                and content[2]==False and len(content[6])<len(last_input_content):
                inp=last_input_content[len(content[6]):]
            else: inp=None
            last_input_content=inp
            pending_output=None
            last_output_time=time.perf_counter()
            output_lines.put(content)
        try:
            while True:
                # Testing thread exception handling
                nonlocal thread_debug
                if thread_debug==1: raise Exception
                elif thread_debug==2: break

                if pending_output!=None:
                    timeout=handler.poll_interval
                else:
                    # Wait longer to reduce CPU usage
                    timeout=0.1
                fds=handler.get_readable_descriptors(timeout)
                foreground_pid=handler.get_foreground_pid()
                # Handle user input from stdin
                if "stdin" in fds:
                    data=handler.read_stdin()
                    if len(data)>0:
                        # Replace Windows keystroke sequences with corresponding characters
                        windows_input_expr=rb"\x1b\[\d+;\d+;(?P<char>\d+);(?P<pressed>\d+);\d+;\d+_"
                        def subst_sequences(match_obj: re.Match) -> bytes:
                            # Ignore char=0 and keystroke release
                            if int(match_obj.group('char'))!=0 and int(match_obj.group('pressed'))!=0:
                                return chr(int(match_obj.group('char'))).encode('utf-8')
                            else: return b''
                        target_input=re.sub(windows_input_expr, subst_sequences, data)
                        # if input from last iteration did not end with newlines, append new content
                        if last_input_content!=None: last_input_content+=target_input
                        else: last_input_content=target_input
                        handler.write_pty(data)
                # Handle output from stdout and stderr
                def handle_output(is_stderr: bool) -> bool:
                    nonlocal pending_output, last_input_content, foreground_pid

                    term_attrs=handler.get_term_attrs(make_raw=True)
                    data=handler.read_pty(is_stderr=is_stderr)
                    # If pipe closed and returns empty data, ignore
                    if data==b'': return False

                    # region: Check if the output is user input
                    do_subst_operation=True
                    if last_input_content!=None:
                        if pending_output!=None: cur_output=pending_output[0]+data
                        else: cur_output=data

                        target_input=last_input_content
                        # If last input content starts with output
                        startswith_output=b'^'+re.sub(rb"(\x08\\ \x08|\\\r\\ \\\r|\x08\x1b\\\[K)", rb"(\\x7f|\\x08)", re.escape(cur_output))
                        # print(target_input, startswith_output, re.match(startswith_output, target_input)!=None) # DEBUG

                        # equals_input=b'^'+re.sub(rb"(\x7f|\x08)", rb"(\\x08 \\x08|\\x08\\x1b\\[K)", re.escape(target_input))+b'$'
                        # if re.match(equals_input, cur_output)!=None:
                        if re.match(startswith_output, target_input)!=None: # Matches from start
                            do_subst_operation=False
                    # endregion
                    pending_output_time=time.perf_counter()
                    if pending_output!=None:
                        orig_data=pending_output[0]
                        if pending_output[3]==foreground_pid and pending_output[1]==is_stderr:
                            # If exceeds maximum time
                            if time.perf_counter()-pending_output[5]>0.1:
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
                    # If all data was pushed, don't do anything
                    if data==b'': return True
                    
                    # Update pending output
                    pending_output=(data,is_stderr,do_subst_operation, foreground_pid, term_attrs, pending_output_time, re.sub(rb"(\x08 \x08|\r \r|\x08\x1b\[K)", b"\x08",data))
                    return True
                had_output=False
                if "stdout" in fds:
                    had_output=had_output or handle_output(is_stderr=False)
                if "stderr" in fds:
                    had_output=had_output or handle_output(is_stderr=True)
                no_io_available=not "stdin" in fds and not had_output
                # Reset last input content after some timeout
                if no_io_available: last_input_content=None
                # if no output available and output delay exceeds poll interval, push the output directly
                if not had_output and time.perf_counter()-last_output_time>=handler.poll_interval \
                    and pending_output!=None:
                    push_output(pending_output)
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
    exit_code=None
    while True:
        try:
            if not thread_exception_handled and not thread.is_alive() and not handler.get_proc_status()!=None:
                raise RuntimeError("Output read loop terminated unexpectedly")
            if thread_exception_handled: 
                exit_code=1
                break # Prevent conflict with setting terminal attributes

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
                try: 
                    new_output, changed_lines=_substrules_processor.match_content(new_output, ' '.join(command), is_stderr=block_data[1], pids=(handler.process_pid, foreground_pid))
                except TimeoutError: failed=True
            new_output=_process_debug([m.group() for m in re.finditer(_globalvar.line_match_bytes, new_output)][:-1], debug_mode, is_stderr=block_data[1], matched_lines=changed_lines, failed=failed, do_subst=block_data[2])
            output+=new_output
            # Print message if foreground process changed and not user input
            if block_data[2]==True: handle_debug_pgrp(block_data[3])
            # update terminal attributes from what the program sets
            if block_data[4]!=None: handler.set_host_term_attrs(block_data[4])
            # subst operation and print output
            handler.write_output(output, is_stderr=block_data[1])
        except direct_exit as exc: # Keyboard interrupt from posix handler
            exit_code=exc.code
            break
        except: 
            exit_code=1
            handle_exception()
            break
    c=handler.handle_exit()
    return exit_code if exit_code!=None else c
