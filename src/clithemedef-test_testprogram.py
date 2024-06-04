import shutil
from clitheme import _generator
from clitheme import _globalvar
import random
import string
import os
l=__file__.split(os.sep)
l.pop()
root_directory="" # directory where the script files are in
for part in l:
    root_directory+=part+os.sep
print("Testing generator function...")
mainfile_data=open(root_directory+"/testprogram-data/clithemedef-test_mainfile.clithemedef.txt",'r', encoding="utf-8").read()
expected_data=open(root_directory+"/testprogram-data/clithemedef-test_expected.txt",'r', encoding="utf-8").read()
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
            print("File "+rootpath+"/"+current_path+" OK")
        except FileNotFoundError:
            print("[File] file "+rootpath+"/"+current_path+" does not exist")
            errorcount+=1
        if contents=="": continue
        if contents.strip()!=line.strip():
            print("[Content] Content mismatch on file "+rootpath+"/"+current_path)
            errorcount+=1
        current_path=""

# Test frontend
print("Testing frontend...")
from clitheme import frontend
frontend.global_lang="en_US.UTF-8"
frontend.global_debugmode=True
frontend.data_path=generator_path+"/"+_globalvar.generator_data_pathname
expected_data_frontend=open(root_directory+"/testprogram-data/clithemedef-test_expected-frontend.txt", 'r', encoding="utf-8").read()
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
            entry_path=_globalvar.splitarray_to_string(phrases[2:]) # just being lazy here
        else:
            descriptor=frontend.FetchDescriptor()
            entry_path=current_path_frontend
        expected_content=line.strip()
        fallback_string=""
        for x in range(30): # reduce inaccuracies
            fallback_string+=random.choice(string.ascii_letters)
        recieved_content=descriptor.retrieve_entry_or_fallback(entry_path, fallback_string)
        if expected_content.strip()!=recieved_content.strip():
            if recieved_content.strip()==fallback_string:
                print("[Error] Failed to retrieve entry for \""+current_path_frontend+"\"")
            else:
                print("[Content] Content mismatch on path \""+current_path_frontend+"\"")
            errorcount_frontend+=1
        current_path_frontend=""
print("\n\nTest results:")
print("==> ",end='')
if errorcount>0:
    print("Generator test error: "+str(errorcount)+" errors found")
    print("See "+generator_path+" for more details")
    exit(1)
else:
    print("Generator test OK")
    shutil.rmtree(generator_path) # remove the temp directory
print("==> ",end='')
if errorcount_frontend>0:
    print("Frontend test error: "+str(errorcount_frontend)+" errors found")
    exit(1)
else:
    print("Frontend test OK")