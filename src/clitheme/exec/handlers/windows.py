# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import time
import ctypes
import io
import stat
from ctypes import wintypes
from typing import Optional, Any, List, Tuple, Union
from ... import _globalvar
from .base_template import BaseHandler
from .windows_headers import *

def errmsg() -> str:
    buffer = ctypes.create_unicode_buffer(1024)
    result = kernel32.FormatMessageW(
        FORMAT_MESSAGE_FROM_SYSTEM,
        None, # lpSource: None for system error
        ctypes.GetLastError(),
        0, # dwLanguageId: 0 to use system language
        buffer,
        ctypes.sizeof(buffer) // ctypes.sizeof(wintypes.WCHAR),
        None # Arguments: None for this one
    )
    if result==0: message="(Unknown error)"
    else: message=buffer.value
    return message

def w_assert(condition, msg: Optional[str]=None):
    if not condition:
        raise OSError(errmsg() if msg==None else msg)

class WindowsHandler(BaseHandler):
    def __init__(self, command: List):
        """
        Perform init

        - Open terminal pipes and pseudo console
        - Set initial window size
        - Initialize process
        - Snapshot of initial attributes
        - Set term attributes for first time
        - Add signal handlers
        """
        self.process_pid: int
        ## Create communication channels
        inputReadSide = wintypes.HANDLE()
        inputWriteSide = wintypes.HANDLE()
        outputReadSide = wintypes.HANDLE()
        outputWriteSide = wintypes.HANDLE()
        # https://learn.microsoft.com/en-us/windows/win32/procthread/creating-a-child-process-with-redirected-input-and-output
        # Make pipes inheritable first
        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.bInheritHandle = True # VERY Important!
        sa.lpSecurityDescriptor = None
        # Create input pipe
        w_assert(kernel32.CreatePipe(ctypes.byref(inputReadSide), ctypes.byref(inputWriteSide), ctypes.byref(sa), 0))
        # Create output pipe
        w_assert(kernel32.CreatePipe(ctypes.byref(outputReadSide), ctypes.byref(outputWriteSide), ctypes.byref(sa), 0))
        # [Optional] Disable inheritance for parent process handles to prevent issues
        w_assert(kernel32.SetHandleInformation(outputReadSide, HANDLE_FLAG_INHERIT, 0))
        w_assert(kernel32.SetHandleInformation(inputWriteSide, HANDLE_FLAG_INHERIT, 0))

        try:
            host_size=os.get_terminal_size()
            term_size = COORD(host_size.columns, host_size.lines)
        except OSError:
            term_size = COORD(80,24)
        ## Create pseudo console
        self.console_handle = wintypes.HANDLE() # HPCON
        w_assert(kernel32.CreatePseudoConsole(
                term_size,
                inputReadSide,
                outputWriteSide,
                PSEUDOCONSOLE_INHERIT_CURSOR, # Don't clear the screen
                ctypes.byref(self.console_handle)
        )==S_OK)

        ## Set startup info
        si = STARTUPINFOEX()
        si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEX)
        # Handle piped stdout
        if stat.S_ISFIFO(os.stat(sys.stdout.fileno()).st_mode):
            # [Use regular pipe instead]
            si.StartupInfo.hStdInput=inputReadSide
            si.StartupInfo.hStdOutput=outputWriteSide
            si.StartupInfo.hStdError=outputWriteSide
            si.StartupInfo.dwFlags=STARTF_USESTDHANDLES # use std handles specified above
        else:
            # [Use pseudoconsole]
            # region: Initialize lpAttributeList
            # Determine the size required for the list
            bytesRequired = ctypes.c_size_t()
            # [Returns error in first call]
            kernel32.InitializeProcThreadAttributeList(
                None,  # NULL pointer to get required size
                1,     # dwAttributeCount (1 attribute)
                0,     # dwFlags
                ctypes.byref(bytesRequired)
            )
            # Allocate memory to represent the list
            si.lpAttributeList = kernel32.HeapAlloc(kernel32.GetProcessHeap(), 0, bytesRequired)
            w_assert(si.lpAttributeList, "Cannot allocate lpAttributeList")
            # Initialize the list memory location
            w_assert(kernel32.InitializeProcThreadAttributeList(
                si.lpAttributeList,
                1,     # dwAttributeCount (1 attribute)
                0,     # dwFlags
                ctypes.byref(bytesRequired)
            ))
            # endregion
            # Set the pseudoconsole information into attribute list
            w_assert(kernel32.UpdateProcThreadAttribute(
                si.lpAttributeList,
                0,  # dwFlags
                PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                self.console_handle,
                ctypes.sizeof(self.console_handle),
                None,  # lpPreviousValue
                None   # lpReturnSize
            ))

        ## Start process

        pi = PROCESS_INFORMATION()
        w_assert(kernel32.CreateProcessW(
            None,  # lpApplicationName
            _globalvar.splitarray_to_string(command),  # lpCommandLine
            None,  # lpProcessAttributes
            None,  # lpThreadAttributes
            True, # bInheritHandles: VERY Important!
            EXTENDED_STARTUPINFO_PRESENT, # dwCreationFlags
            None,  # lpEnvironment
            None,  # lpCurrentDirectory
            ctypes.byref(si),  # lpStartupInfo
            ctypes.byref(pi)  # lpProcessInformation
        ))
        self.process_pid=int(pi.dwProcessId)
        self.process_handle=pi.hProcess
        ## Set terminal attributes
        # Save initial attributes
        self.prev_attrs=self.get_process_term_attrs()
        # Update terminal attributes
        attrs=self.get_process_term_attrs(no_buffering=True)
        if attrs!=None: self.set_host_term_attrs(attrs)

        self.stdin_fd=inputWriteSide
        self.stdout_fd=outputReadSide

        # The Pseudoconsole outputs these sets of control sequences before process output:
        # 1. Query cursor position, when PSEUDOCONSOLE_INHERIT_CURSOR is specified
        # 2. Setup additional console modes (e.g. Focus event reporting, UTF-8 edit mode)
        # These set of sequences are VERY important and MUST be directly written to output!
        self.init_seq_left=2

        # The last line of console output might end with '\r'
        # In this case, output '\n' when exiting
        self.ends_with_R=False

    def _get_std_handles(self) -> Tuple[wintypes.HANDLE, wintypes.HANDLE]:
        stdin_handle=kernel32.GetStdHandle(STD_INPUT_HANDLE)
        w_assert(stdin_handle!=INVALID_HANDLE_VALUE)
        stdout_handle=kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        w_assert(stdout_handle!=INVALID_HANDLE_VALUE)
        return (stdin_handle, stdout_handle)
    def _read_data(self, handle: wintypes.HANDLE) -> bytes:
        buf=ctypes.create_string_buffer(io.DEFAULT_BUFFER_SIZE)
        bytes_read=wintypes.DWORD()
        w_assert(kernel32.ReadFile(handle, ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(bytes_read), None))
        return buf.value[:bytes_read.value]
    def _write_data(self, handle: wintypes.HANDLE, data: Union[bytes, str]):
        handle_type=kernel32.GetFileType(handle)
        w_assert(handle_type!=FILE_TYPE_UNKNOWN)
        if handle_type==FILE_TYPE_CHAR: # str
            try:
                if type(data)==bytes: data=data.decode('utf-8')
                buf=ctypes.create_unicode_buffer(data) # type: ignore
                w_assert(kernel32.WriteConsoleW(handle,
                        ctypes.byref(buf),
                        ctypes.sizeof(buf) // ctypes.sizeof(wintypes.WCHAR),
                        None, None))
            except UnicodeDecodeError:
                buf=ctypes.create_string_buffer(data) # type: ignore
                w_assert(kernel32.WriteFile(handle, ctypes.byref(buf), len(data), None, None))
        elif handle_type==FILE_TYPE_PIPE: # bytes
            if type(data)==str: data=data.encode('utf-8')
            buf=ctypes.create_string_buffer(data) # type: ignore
            w_assert(kernel32.WriteFile(handle, ctypes.byref(buf), len(data), None, None))
        else: raise AssertionError("Unsupported handle type")
    def read_stdin(self) -> bytes:
        stdin_handle=self._get_std_handles()[0]
        stdin_type=kernel32.GetFileType(stdin_handle)
        w_assert(stdin_type!=FILE_TYPE_UNKNOWN)
        if stdin_type==FILE_TYPE_CHAR:
            events_read = wintypes.DWORD()
            input_records = INPUT_RECORD_arr()
            arr_size=input_records._length_
            w_assert(kernel32.ReadConsoleInputW(stdin_handle, ctypes.byref(input_records), arr_size, ctypes.byref(events_read)))
            total_data=b''
            for x in range(events_read.value):
                record=input_records[x]
                if record.EventType==KEY_EVENT:
                    key_event=record.Event.KeyEvent
                    if key_event.bKeyDown:
                        total_data+=key_event.uChar.UnicodeChar.encode('utf-8')*key_event.wRepeatCount
                elif record.EventType==WINDOW_BUFFER_SIZE_EVENT:
                    coord=record.Event.WindowBufferSizeEvent.dwSize
                    w_assert(kernel32.ResizePseudoConsole(self.console_handle, coord)==S_OK)
            return total_data
        elif stdin_type==FILE_TYPE_PIPE:
            return self._read_data(stdin_handle)
        else: raise ValueError("Standard input is not a pipe or console")
    def write_output(self, data: bytes, is_stderr: bool=False):
        if is_stderr: raise NotImplementedError
        self._write_data(self._get_std_handles()[1], data)
    def read_pty(self, is_stderr: bool=False) -> bytes:
        if is_stderr: raise NotImplementedError
        data=self._read_data(self.stdout_fd)
        
        self.ends_with_R=data.endswith(b'\r')
        # If initial sequences doesn't start with ESC, always assume process output
        if not data.startswith(b'\x1b'): self.init_seq_left=0
        # Handle initial control sequences: Write directly to output
        if self.init_seq_left>0:
            self.write_output(data)
            self.init_seq_left-=1
            return b''
        else: return data
    def write_pty(self, data: bytes):
        self._write_data(self.stdin_fd, data)
    def _read_available(self, handle) -> bool:
        # Check if available for reading
        handle_type=kernel32.GetFileType(handle)
        w_assert(handle_type!=FILE_TYPE_UNKNOWN)
        bytes_available = wintypes.DWORD()
        if handle_type==FILE_TYPE_CHAR:
            w_assert(kernel32.GetNumberOfConsoleInputEvents(handle, ctypes.byref(bytes_available)))
        elif handle_type==FILE_TYPE_PIPE:
            w_assert(kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(bytes_available), None))
        else: raise AssertionError("Unsupported handle type")
        return bytes_available.value>0
    def get_readable_descriptors(self, timeout: float) -> List:
        # Possible values: ["stdin", "stdout", "stderr"]
        init_time=time.perf_counter()
        # Simulate timeout
        counter=0
        while counter==0 or time.perf_counter()-init_time<timeout:
            counter+=1

            avail_handles=[]
            stdin_handle=self._get_std_handles()[0]
            # stdin
            try:
                if self._read_available(stdin_handle):
                    avail_handles.append("stdin")
            except AssertionError: pass
            # stdout
            try:
                if self._read_available(self.stdout_fd):
                    avail_handles.append("stdout")
            except AssertionError: pass
            if len(avail_handles)!=0: return avail_handles
            time.sleep(0.001)
        return []
    def get_process_term_attrs(self, no_buffering=False) -> Optional[Any]:
        try:
            stdin_handle, stdout_handle=self._get_std_handles()
            input_mode=wintypes.DWORD()
            w_assert(kernel32.GetConsoleMode(stdin_handle, ctypes.byref(input_mode)))
            output_mode=wintypes.DWORD()
            w_assert(kernel32.GetConsoleMode(stdout_handle, ctypes.byref(output_mode)))
            if no_buffering:
                input_mode.value &= ~(ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT)
                input_mode.value |= ENABLE_VIRTUAL_TERMINAL_INPUT
                output_mode.value |= ENABLE_PROCESSED_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            return [input_mode.value, output_mode.value]
        except AssertionError: return None
    def set_host_term_attrs(self, term_attrs):
        try:
            stdin_handle, stdout_handle=self._get_std_handles()
            w_assert(kernel32.SetConsoleMode(stdin_handle, term_attrs[0]))
            w_assert(kernel32.SetConsoleMode(stdout_handle, term_attrs[1]))
        except AssertionError: return None
    def get_foreground_pid(self) -> Optional[int]:
        # Not applicable for Windows processes
        return None
    def get_proc_status(self) -> Optional[int]:
        # Returns None if running; returns exit code if finished
        exit_code=wintypes.DWORD()
        w_assert(kernel32.GetExitCodeProcess(self.process_handle, ctypes.byref(exit_code)))
        if exit_code.value == STILL_ACTIVE: return None
        else: return exit_code.value
    def reset_terminal(self):
        if self.prev_attrs!=None: self.set_host_term_attrs(self.prev_attrs) # restore previous attributes
        if not stat.S_ISFIFO(os.stat(sys.stdout.fileno()).st_mode):
            self.write_output(b"\x1b[0m\x1b[?1;1000;1001;1002;1003;1005;1006;1015;1016l\n\x1b[J") # reset color, mouse reporting, and clear the rest of the screen
    def handle_exit(self) -> int:
        if self.ends_with_R: self.write_output(b'\n')
        # Unset UTF-8 extended edit mode to prevent issues with some apps
        if not stat.S_ISFIFO(os.stat(sys.stdout.fileno()).st_mode):
            self.write_output(b'\x1b[?9001l') 
        # Close handles when done
        w_assert(kernel32.CloseHandle(self.stdin_fd))
        w_assert(kernel32.CloseHandle(self.stdout_fd))
        w_assert(kernel32.ClosePseudoConsole(self.console_handle)==None)
        # Restore console mode
        if self.prev_attrs!=None:
            self.set_host_term_attrs(self.prev_attrs)
        # Return exit code
        exit_code=self.get_proc_status()
        return exit_code if exit_code!=None else 0
