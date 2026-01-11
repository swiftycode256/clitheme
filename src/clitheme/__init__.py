"""
Command line customization toolkit
"""
# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__=["frontend"] 

# Enable processing of escape characters in Windows Command Prompt
import os
if os.name=="nt":
    import ctypes
    try:
        handle=ctypes.windll.kernel32.GetStdHandle(-11) # standard output handle
        console_mode=ctypes.c_long()
        assert ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(console_mode))
        console_mode.value|=0x0004 # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        assert ctypes.windll.kernel32.SetConsoleMode(handle, console_mode.value)
    except: pass
    del ctypes
del os

# Expose these modules when "clitheme" is imported
from . import frontend
# Set localization files
from . import _globalvar
_globalvar.handle_set_themedef(debug_name="global")
del _globalvar # Don't expose this module