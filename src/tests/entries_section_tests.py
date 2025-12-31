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

# spell-checker:ignore rootpath errorcount mainfile

l=__file__.split(os.sep)
l.pop()
root_directory="" # directory where the script files are in
for part in l:
    root_directory+=part+os.sep
print("Testing generator function...")
mainfile_data=open(root_directory+"/entries_test_data/mainfile.clithemedef.txt",'r', encoding="utf-8").read()
expected_data=open(root_directory+"/entries_test_data/expected.txt",'r', encoding="utf-8").read()
generator_path=_generator.generate_data_hierarchy(mainfile_data)

errorcount=0
rootpath=generator_path+"/"+_globalvar.generator_data_pathname
current_path=""
for line in expected_data.splitlines():
    if line.strip()=='' or line.strip()[0]=='#':
        continue
    if current_path=="": # on path line
        current_path=line.strip()
    else: # on content line
        # read the file
        contents=""
        try:
            contents=open(rootpath+"/"+current_path, 'r', encoding="utf-8").read()
            # print("File "+rootpath+"/"+current_path+" OK")
        except FileNotFoundError:
            print("[File] file "+rootpath+"/"+current_path+" does not exist")
            errorcount+=1
            current_path=""
        if contents=="": continue
        if contents.strip()!=line.strip():
            print("[Content] Content mismatch on file "+rootpath+"/"+current_path)
            errorcount+=1
        current_path=""

# Test frontend
print("\nTesting frontend...")
frontend.set_debugmode(True)
frontend.set_lang("en_US.UTF-8")
frontend.data_path=generator_path+"/"+_globalvar.generator_data_pathname
expected_data_frontend=open(root_directory+"/entries_test_data/expected-frontend.txt", 'r', encoding="utf-8").read()
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
        msg=io.StringIO()
        sys.stdout=msg
        received_content=descriptor.retrieve_entry_or_fallback(entry_path, fallback_string)
        sys.stdout=sys.__stdout__
        if expected_content.strip()!=received_content.strip():
            print() # Newline
            if received_content.strip()==fallback_string:
                print("[Error] Failed to retrieve entry for \""+current_path_frontend+"\":")
            else:
                print("[Content] Content mismatch on path \""+current_path_frontend+"\":")
            errorcount_frontend+=1
            print(msg.getvalue(), end='')
        current_path_frontend=""
print("\nTest results:")
print("==> ",end='')
if errorcount>0:
    print("Generator test error: "+str(errorcount)+" errors found")
    print("See "+generator_path+" for more details")
    exit(1)
else:
    print("Generator test OK")
print("==> ",end='')
if errorcount_frontend>0:
    print("Frontend test error: "+str(errorcount_frontend)+" errors found")
    print("See "+generator_path+" for more details")
    exit(1)
else:
    print("Frontend test OK")
if errorcount>0 and errorcount_frontend>0:
    shutil.rmtree(generator_path) # remove the temp directory