# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import shutil
import random
import string
import os
import io
import sys
sys.path=[f"{os.path.dirname(__file__)}/.."]+sys.path
from clitheme import frontend
from clitheme import _generator, _globalvar
import unittest
import warnings

class TestEntriesSection(unittest.TestCase):
    def setUp(self):
        print()
        warnings.simplefilter("ignore")
        self.mainfile_data=open(os.path.dirname(__file__)+"/entries_test_data/mainfile.ctdef.txt",'r', encoding="utf-8").read()
        self.expected_data=open(os.path.dirname(__file__)+"/entries_test_data/expected.txt",'r', encoding="utf-8").read()
        self.generator_path=_generator.generate_data_hierarchy(self.mainfile_data)
        _generator.silence_warn=True # Don't show warnings for second time
        self.rootpath=self.generator_path+"/"+_globalvar.generator_data_pathname
    def tearDown(self):
        shutil.rmtree(self.generator_path)
    def test1_generator(self):
        errorcount=0
        current_path=""
        for line in self.expected_data.splitlines():
            if line.strip()=='' or line.strip()[0]=='#':
                continue
            if current_path=="": # on path line
                current_path=line.strip()
            else: # on content line
                # read the file
                contents=""
                try:
                    contents=open(self.rootpath+"/"+current_path, 'r', encoding="utf-8").read()
                    # print("File "+self.rootpath+"/"+current_path+" OK")
                except FileNotFoundError:
                    print("[File] file "+self.rootpath+"/"+current_path+" does not exist")
                    errorcount+=1
                    current_path=""
                if contents=="": continue
                if contents.strip()!=line.strip():
                    print("[Content] Content mismatch on file "+self.rootpath+"/"+current_path)
                    errorcount+=1
                current_path=""
        self.assertEqual(errorcount, 0)
    def test2_frontend(self):
        frontend.set_debugmode(True)
        frontend.set_lang("en_US.UTF-8")
        frontend.data_path=self.rootpath
        expected_data_frontend=open(os.path.dirname(__file__)+"/entries_test_data/expected-frontend.txt", 'r', encoding="utf-8").read()
        current_path_frontend=""
        errorcount_frontend=0
        for line in expected_data_frontend.splitlines():
            if line.strip()=='' or line.strip()[0]=='#':
                continue
            if current_path_frontend=="": # on path line
                current_path_frontend=line.strip()
            else: # on content line
                phrases=current_path_frontend.split()
                descriptor=None
                entry_path=None
                if len(phrases)>2:
                    descriptor=frontend.FetchDescriptor(domain_name=phrases[0],app_name=phrases[1])
                    entry_path=' '.join(phrases[2:]) # just being lazy here
                else:
                    descriptor=frontend.FetchDescriptor()
                    entry_path=current_path_frontend
                expected_content=line.strip()
                fallback_string=""
                for x in range(30): # reduce inaccuracies
                    fallback_string+=random.choice(string.ascii_letters)
                orig_stdout=sys.stdout
                msg=io.StringIO()
                sys.stdout=msg
                received_content=descriptor.retrieve_entry_or_fallback(entry_path, fallback_string)
                sys.stdout=orig_stdout
                if expected_content.strip()!=received_content.strip():
                    print() # Newline
                    if received_content.strip()==fallback_string:
                        print("[Error] Failed to retrieve entry for \""+current_path_frontend+"\":")
                    else:
                        print("[Content] Content mismatch on path \""+current_path_frontend+"\":")
                    errorcount_frontend+=1
                    print(msg.getvalue(), end='')
                current_path_frontend=""
if __name__ == "__main__":
    unittest.main()