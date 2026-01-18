# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


import subprocess
import sys
import os
import io
import pty
import tty
import termios
import stat
import fcntl
import signal
import select
import struct
import copy
import threading
from typing import Optional
from ... import _frontend_internal as frontend, _globalvar
from ..._globalvar import direct_exit
from .. import _labeled_print
from ._base_template import BaseHandler, command_failed

# spell-checker:ignore RDWR

fd=frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="exec")

class PosixHandler(BaseHandler):
    poll_interval=0.01

    def __init__(self, command):
        """
        Perform init

        - Open terminal descriptors
        - Initialize process
        - Snapshot of prev attributes
        - Set term attributes for first time
        - Set initial window size
        - Add signal handlers
        """

        env=copy.copy(os.environ)
        # Prevent apps from using "less" or "more" as pager, as it won't work here
        env['PAGER']="cat"

        # Open terminal descriptors
        # Detect if stdout/stderr is piped (e.g. clitheme-exec curl --help|cat)
        if stat.S_ISFIFO(os.stat(sys.stdout.fileno()).st_mode):
            self.stdout_fd, self.stdout_child=os.pipe()
        else: 
            self.stdout_fd, self.stdout_child=pty.openpty()
        if stat.S_ISFIFO(os.stat(sys.stderr.fileno()).st_mode):
            self.stderr_fd, self.stderr_child=os.pipe()
        else:
            self.stderr_fd, self.stderr_child=pty.openpty()
        # Detect if stdin is piped (e.g. cat file|clitheme-exec grep content)
        stdin_fd=self.stdout_child
        pipe_thread=None
        if stat.S_ISFIFO(os.stat(sys.stdin.fileno()).st_mode):
            r,w=os.pipe()
            def pipe_forward():
                # Background thread to forward stdin to subprocess pipe
                nonlocal r,w
                while True:
                    d=os.read(sys.stdin.fileno(), io.DEFAULT_BUFFER_SIZE)
                    if d==b'': # stdin is closed
                        os.close(w)
                        # Duplicate stdout terminal onto stdin to read user input
                        if os.isatty(sys.stdout.fileno()):
                            os.dup2(sys.stdout.fileno(), sys.stdin.fileno())
                        break
                    os.write(w,d)
            pipe_thread=threading.Thread(target=pipe_forward, daemon=True)
            stdin_fd=r
        # Initialize process
        def child_init():
            # Must start new session or some programs might not work properly
            os.setsid()

            for fd in (self.stdout_child, self.stderr_child):
                if os.isatty(fd):
                    # Make controlling terminal so programs can access TTY properly
                    # [Explicitly open the tty to make it become a controlling tty.]
                    # --From source code of pty.fork()--
                    tmp_fd = os.open(os.ttyname(fd), os.O_RDWR)
                    os.close(tmp_fd)
        try:
            self.process=subprocess.Popen(command, stdin=stdin_fd, stdout=self.stdout_child, stderr=self.stdout_child, env=env, preexec_fn=child_init)
        except:
            raise command_failed(str(sys.exc_info()[1]))
        if pipe_thread!=None:
            # Must start only after initiating process
            pipe_thread.start()
        self.process_pid=self.process.pid

        # Terminal attributes
        self.prev_attrs=self.get_term_attrs()
        # Set term attributes for first time
        attrs=self.get_term_attrs(make_raw=True)
        if attrs!=None: self.set_host_term_attrs(attrs)
        
        # Set initial window size
        self.last_terminal_size=None
        self.update_window_size()

        # Setup signal handlers
        self.handle_signals=[signal.SIGTSTP, signal.SIGCONT, signal.SIGINT, signal.SIGQUIT]
        for sig in self.handle_signals:
            signal.signal(sig, self._signal_handler_function)
        signal.signal(signal.SIGWINCH, self.update_window_size)
        
    def read_stdin(self) -> bytes:
        return os.read(sys.stdin.fileno(), io.DEFAULT_BUFFER_SIZE)
    def write_output(self, data: bytes, is_stderr: bool=False):
        os.write(sys.stderr.fileno() if is_stderr else sys.stdout.fileno(),data)
    def read_pty(self, is_stderr: bool=False) -> bytes:
        return os.read(self.stderr_fd if is_stderr else self.stdout_fd, io.DEFAULT_BUFFER_SIZE)
    def write_pty(self, data: bytes):
        os.write(self.stdout_fd, data)
    def get_readable_descriptors(self, timeout: float) -> set:
        # Possible values: ["stdin", "stdout", "stderr"]
        try: fds=select.select([self.stdout_fd, sys.stdin, self.stderr_fd], [], [], timeout)[0]
        except OSError: fds=select.select([self.stdout_fd, self.stderr_fd], [], [], timeout)[0]
        fd_names=set()
        for pair in [(sys.stdin, "stdin"), (self.stdout_fd, "stdout"), (self.stderr_fd, "stderr")]:
            if pair[0] in fds: fd_names.add(pair[1])
        return fd_names
    def get_window_size(self):
        return fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH',0,0,0,0))
    def update_window_size(self, *args):
        # update terminal size
        try:
            new_term_size=self.get_window_size()
            if new_term_size!=self.last_terminal_size:
                self.last_terminal_size=new_term_size
                fcntl.ioctl(self.stdout_fd, termios.TIOCSWINSZ, new_term_size)
                fcntl.ioctl(self.stderr_fd, termios.TIOCSWINSZ, new_term_size)
                self.process.send_signal(signal.SIGWINCH)
        except: pass
    def get_term_attrs(self, make_raw=False) -> Optional[list]:
        try:
            term_attrs=termios.tcgetattr(sys.stdout.fileno())
            if make_raw:
                # spell-checker:disable
                # Set raw mode (from Python 3.14 tty.cfmakeraw function)
                # Clear all POSIX.1-2017 flags
                term_attrs[tty.IFLAG] &= ~(termios.IGNBRK | termios.BRKINT | termios.IGNPAR | termios.PARMRK | termios.INPCK | termios.ISTRIP | termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IXON | termios.IXANY | termios.IXOFF)
                term_attrs[tty.OFLAG] &= ~termios.OPOST
                term_attrs[tty.CFLAG] &= ~(termios.PARENB | termios.CSIZE)
                term_attrs[tty.CFLAG] |= termios.CS8
                term_attrs[tty.LFLAG] &= ~(termios.ECHO | termios.ECHOE | termios.ECHOK | termios.ECHONL | termios.ICANON | termios.IEXTEN | termios.ISIG | termios.NOFLSH | termios.TOSTOP)

                try: child_attrs=termios.tcgetattr(self.stdout_fd)
                except termios.error: pass
                else:
                    # Use character settings from child process
                    term_attrs[tty.CC]=child_attrs[tty.CC]
                    # If not disabled by child process, enable ISIG for proper signal handling
                    if child_attrs[tty.LFLAG] & termios.ISIG > 0:
                        term_attrs[tty.LFLAG] |= termios.ISIG
                # Ensure settings are correct for non-canonical input mode
                term_attrs[tty.CC][termios.VMIN] = 1
                term_attrs[tty.CC][termios.VTIME] = 0
                # spell-checker:enable
            return term_attrs
        except termios.error: return None
    def set_host_term_attrs(self, term_attrs: list):
        try:
            termios.tcsetattr(sys.stdout, termios.TCSADRAIN, term_attrs)
        except termios.error: pass
    def _reset_term_attrs(self):
        if self.prev_attrs!=None: self.set_host_term_attrs(self.prev_attrs) # restore previous attributes
    def get_foreground_pid(self) -> Optional[int]:
        try: 
            value=os.tcgetpgrp(self.stdout_fd)
            if value==0: return self.process_pid
            else: return value
        except OSError: return None
    def _signal_handler_function(self, sig, frame):
        if sig==signal.SIGCONT: # continue signal
            self.process.send_signal(sig)
            # Reset signal handler
            signal.signal(signal.SIGTSTP, self._signal_handler_function)
            # Set term attributes after re-entering
            attrs=self.get_term_attrs(make_raw=True)
            if attrs!=None: self.set_host_term_attrs(attrs)
        elif sig==signal.SIGTSTP: # suspend signal
            if self.get_foreground_pid()!=self.process_pid: # e.g. A shell running another process
                if self.process.poll()==None: # Process is running
                    self.write_pty(b'\x1a') # Send '^Z' character; don't suspend the entire shell
            else: 
                self._reset_term_attrs()
                self.process.send_signal(signal.SIGSTOP) # Stop the process
                signal.signal(signal.SIGTSTP, signal.SIG_DFL) # Unset signal handler to prevent deadlock
                os.kill(os.getpid(), signal.SIGTSTP) # Suspend itself
        elif sig==signal.SIGINT:
            if self.process.poll()==None:
                self.write_pty(b'\x03') # '^C' character
            else:
                self.reset_terminal()
                _labeled_print(fd.reof("output-interrupted-exit", "Output interrupted after command exit"))
                # Prevent message being triggered multiple times
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                raise direct_exit(130) # Will be raised in main processing loop
        elif sig==signal.SIGQUIT:
            if self.process.poll()==None:
                os.write(self.stdout_fd, b'\x1c') # '^\' character
    def get_proc_status(self) -> Optional[int]:
        return self.process.poll()
    def reset_terminal(self):
        self._reset_term_attrs()
        if not stat.S_ISFIFO(os.stat(sys.stdout.fileno()).st_mode):
            self.write_output(b"\x1b[0m\x1b[?1;1000;1001;1002;1003;1005;1006;1015;1016l\r\n\x1b[J") # reset color, mouse reporting, and clear the rest of the screen
    def handle_exit(self) -> int:
        self._reset_term_attrs()
        exit_code=self.get_proc_status()
        try:
            if exit_code!=None and exit_code<0: # Terminated by signal
                # Reset signal handlers before the kill operation to prevent unexpected behavior
                for sig in self.handle_signals+[signal.SIGUSR1, signal.SIGUSR2]:
                    signal.signal(sig, signal.SIG_DFL)
                os.kill(os.getpid(), abs(exit_code))
                # Return exit code if os.kill doesn't terminate process
                return 128+abs(exit_code)
        except: pass
        return exit_code if exit_code!=None else 0