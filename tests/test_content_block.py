# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

# Program for testing multi-line (block) processing of _generator
import sys
import os
import shutil
import tempfile
import pathlib
sys.path=[f"{os.path.dirname(__file__)}/../src"]+sys.path
from clitheme import frontend
import unittest

file_data=r"""
begin_header
    name untitled
end_header

begin_main
    set_options linebounds
    entry test_entry
        locale_block default en_US en C


            this
            and
          | that |

                is just good
                    #enough
         |  should have leading 2 lines and trailing 3 lines   |
            \end_block
            \\end_block



        end_block
    end_entry
    [entry] test_entry-2
        default: |   this and that  |
    [/entry]
end_main
"""

file_data_2=r"""
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
            \[/locale]
            \\[/locale]


        [/locale] leadtabindents:1
    end_entry
    set_options leadspaces:2 linebounds
    setvar:test |that and this  |
    [entry] test_entry-2
        [locale] zh_CN
            |   {{test}}|
        [/locale] linebounds substvar
    [/entry]
end_main
"""

class TestContentBlock(unittest.TestCase):
    def setUp(self):
        print()
        # Remove cache folders
        for path in pathlib.Path(tempfile.gettempdir()).glob("clitheme-data-*"):
            print(f"Remove {path}")
            shutil.rmtree(path)
        frontend.set_debugmode(True)
        if frontend.set_local_themedef(file_data)==False:
            print("Error: set_local_themedef failed")
            exit(1)
        if frontend.set_local_themedef(file_data_2, overlay=True)==False: # test overlay function
            print("Error: set_local_themedef with overlay failed")
            exit(1)
        frontend.set_debugmode(False)
    def disp(self, content: str):
        self.assertNotEqual(content, "Nonexistent")
        print("---")
        for line in content.split('\n'):
            assert not line[-1:]=='\r', r"String entry content should not end in \r\n"
            print(f">{line}|")
        print("---")
        print()
    def test_content_block(self):
        f=frontend.FetchDescriptor()
        print("Default locale:")
        f.disable_lang=True
        self.disp(f.reof("test_entry", "Nonexistent"))
        self.disp(f.reof("test_entry-2", "Nonexistent"))
        print("zh_CN locale:")
        f.disable_lang=False
        f.lang="zh_CN"
        self.disp(f.reof("test_entry", "Nonexistent"))
        self.disp(f.reof("test_entry-2", "Nonexistent"))
        errcount=0
        for lang in ["C", "en", "en_US", "zh_CN"]:
            f.disable_lang=True
            name=f"test_entry__{lang}"
            if f.entry_exists(name):
                print(f"{name} found")
            else:
                print(f"{name} not found")
                errcount+=1
        self.assertEqual(errcount, 0)
if __name__=="__main__":
    unittest.main()
