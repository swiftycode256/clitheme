# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Script to get contents of file inside the module
"""
import os
l=__file__.split(os.sep)
l.pop()
final_str="" # directory where the script files are in
for part in l:
    final_str+=part+os.sep
def read_file(path: str) -> str:
    return open(final_str+os.sep+path, encoding="utf-8").read()