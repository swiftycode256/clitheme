#!/usr/bin/python3

# Program for testing multi-line (block) processing of _generator
from src.clitheme import _generator, frontend, _globalvar

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



        end_block
        locale_block zh_CN



            这是一个
            很好的东西

                #非常好
                    ...
            should have leading 3 lines and trailing 2 lines


        end_block
    end_entry
end_main
"""

_generator.generate_data_hierarchy(file_data)
frontend.data_path=_generator.path+"/"+_globalvar.generator_data_pathname
f=frontend.FetchDescriptor()
print("Default locale:")
f.disable_lang=True
print(f.reof("test_entry", "Nonexistent"))
print("zh_CN locale:")
f.disable_lang=False
f.lang="zh_CN"
print(f.reof("test_entry", "Nonexistent"))

for lang in ["C", "en", "en_US", "zh_CN"]:
    f.disable_lang=True
    name=f"test_entry__{lang}"
    if f.entry_exists(name):
        print(f"{name} OK")
    else:
        print(f"{name} not found")

import sys
if sys.argv.__contains__("--preserve-temp"):
    print(f"View generated data at {_generator.path}")
    exit()

import shutil
shutil.rmtree(_generator.path)