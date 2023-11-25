import shutil
import _generator

mainfile_data=open("tests/clithemedef-test_mainfile.txt",'r').read()
expected_data=open("tests/clithemedef-test_expected.txt",'r').read()
funcresult=_generator.generate_data_hierarchy(mainfile_data)

errorcount=0
rootpath=_generator.path+"/theme-data"
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
        except FileNotFoundError:
            print("[File] file "+rootpath+"/"+current_path+" does not exist")
            errorcount+=1
        if contents=="": continue
        if contents.strip()!=line.strip():
            print("[Content] Content mismatch on file "+rootpath+"/"+current_path)
            errorcount+=1
        current_path=""
if errorcount>0:
    print("Test error: "+str(errorcount)+" errors found")
    print("See "+_generator.path+" for more details")
    exit(1)
else:
    print("Test OK")
    shutil.rmtree(_generator.path) # remove the temp directory