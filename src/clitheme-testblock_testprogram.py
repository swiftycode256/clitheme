#!/usr/bin/python3

# Program for testing multi-line (block) processing of _generator
from clitheme import _generator, frontend

file_data="""
begin_header
    name untitled
end_header

begin_main
    entry test_entry
        locale_block default en_US en C


            this
            and
            that

                is just good
                    #enough
            should have leading 2 lines and trailing 3 lines



        end_block leadtabindents:1
    end_entry
end_main
"""

file_data_2="""
begin_header
    name untitled
end_header

begin_main
    entry test_entry
        locale_block zh_CN



            这是一个
            很好的东西

                #非常好
                    ...
            should have leading 3 lines and trailing 2 lines


        end_block leadspaces:4
    end_entry
end_main
"""

frontend.global_debugmode=True
if frontend.set_local_themedef(file_data)==False:
    print("Error: set_local_themedef failed")
    exit(1)
if frontend.set_local_themedef(file_data_2, overlay=True)==False: # test overlay function
    print("Error: set_local_themedef failed")
    exit(1)
f=frontend.FetchDescriptor()
print("Default locale:")
f.disable_lang=True
# Not printing because debug mode already prints
(f.reof("test_entry", "Nonexistent"))
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

import sys
if "--preserve-temp" in sys.argv:
    print(f"View generated data at {_generator.path}")
    exit()

import shutil
try: shutil.rmtree(_generator.path)
except: print("Warning: failed to remove temp directory \"{}\"".format(_generator.path))