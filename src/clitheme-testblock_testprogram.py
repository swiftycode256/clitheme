# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

# Program for testing multi-line (block) processing of _generator
from clitheme import _generator, frontend

file_data="""
begin_header
    name untitled
end_header

begin_main
    set_options leadtabindents:1 linebounds
    entry test_entry
        locale_block default en_US en C


            this
            and
          | that|

                is just good
                    #enough
        |   should have leading 2 lines and trailing 3 lines|
            \\end_block
            \\\\end_block



        end_block
    end_entry
    [entry] test_entry-2
        locale:default |   this and that  |
    [/entry]
end_main
"""

file_data_2="""
begin_header
    name untitled
end_header

begin_main
    entry test_entry
        [locale] zh_CN



            这是一个
            很好的东西

                #非常好
                    ...
            should have leading 3 lines and trailing 2 lines
            \\[/locale]
            \\\\[/locale]


        [/locale] leadspaces:4
    end_entry
end_main
"""

frontend.set_debugmode(True)
if frontend.set_local_themedef(file_data)==False:
    print("Error: set_local_themedef failed")
    exit(1)
if frontend.set_local_themedef(file_data_2, overlay=True)==False: # test overlay function
    print("Error: set_local_themedef with overlay failed")
    exit(1)
f=frontend.FetchDescriptor()
print("Default locale:")
f.disable_lang=True
# Not printing because debug mode already prints
(f.reof("test_entry", "Nonexistent"))
(f.reof("test_entry-2", "Nonexistent"))
print("zh_CN locale:")
f.disable_lang=False
f.lang="zh_CN"
(f.reof("test_entry", "Nonexistent"))
f.debug_mode=False
for lang in ["C", "en", "en_US", "zh_CN"]:
    f.disable_lang=True
    name=f"test_entry__{lang}"
    if f.entry_exists(name):
        print(f"{name} found")
    else:
        print(f"{name} not found")
