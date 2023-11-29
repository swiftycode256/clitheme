import shutil
import _generator
import _globalvar
import random
import string

print("Testing generator function...")
mainfile_data=open("tests/clithemedef-test_mainfile.txt",'r').read()
expected_data=open("tests/clithemedef-test_expected.txt",'r').read()
funcresult=_generator.generate_data_hierarchy(mainfile_data)

errorcount=0
rootpath=_generator.path+"/"+_globalvar.generator_data_pathname
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
            contents=open(rootpath+"/"+current_path).read()
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
import frontend
frontend.global_lang="en_US.UTF-8"
frontend.data_path=_generator.path+"/"+_globalvar.generator_data_pathname
expected_data_frontend=open("tests/clithemedef-test_expected-frontend.txt", 'r').read()
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
            descriptor=frontend.FetchDescriptor(domain_name=phrases[0],app_name=phrases[1],debug_mode=True)
            entry_path=_generator.splitarray_to_string(phrases[2:]) # just being lazy here
        else:
            descriptor=frontend.FetchDescriptor(debug_mode=True)
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
    print("See "+_generator.path+" for more details")
    exit(1)
else:
    print("Generator test OK")
    shutil.rmtree(_generator.path) # remove the temp directory
print("==> ",end='')
if errorcount_frontend>0:
    print("Frontend test error: "+str(errorcount_frontend)+" errors found")
    exit(1)
else:
    print("Frontend test OK")