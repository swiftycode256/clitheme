# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Optional, Any, List

class BaseHandler:
    """
    Template for handler class
    """
    def __init__(self, command: List):
        self.process_pid: int
        raise NotImplementedError
    def read_stdin(self) -> bytes:
        raise NotImplementedError
    def write_output(self, data: bytes, is_stderr: bool=False):
        raise NotImplementedError
    def read_pty(self, is_stderr: bool=False) -> bytes:
        raise NotImplementedError
    def write_pty(self, data: bytes):
        raise NotImplementedError
    def get_readable_descriptors(self, timeout: float) -> List:
        # Possible values: ["stdin", "stdout", "stderr"]
        # for pair in [(sys.stdin, "stdin"), (self.stdout_fd, "stdout"), (self.stderr_fd, "stderr")]:
        raise NotImplementedError
    def get_window_size(self):
        raise NotImplementedError
    def update_window_size(self, *args):
        raise NotImplementedError
    def get_process_term_attrs(self, no_buffering=False) -> Optional[Any]:
        raise NotImplementedError
    def set_host_term_attrs(self, term_attrs):
        raise NotImplementedError
    def get_foreground_pid(self) -> Optional[int]:
        raise NotImplementedError
    def get_proc_status(self) -> Optional[int]:
        # Returns None if running; returns exit code if finished
        raise NotImplementedError
    def reset_terminal(self):
        raise NotImplementedError
    def handle_exit(self) -> int:
        raise NotImplementedError
