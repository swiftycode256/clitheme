# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__=["frontend", "cli", "man", "exec"] 

# Prevent RuntimeWarning from displaying when running a submodule (e.g. "python3 -m clitheme.exec")
import warnings
warnings.simplefilter("ignore", category=RuntimeWarning)
from . import _globalvar, frontend, cli, man, exec
_globalvar.handle_set_themedef(frontend, "global") # type: ignore
del _globalvar # Don't expose this module by default