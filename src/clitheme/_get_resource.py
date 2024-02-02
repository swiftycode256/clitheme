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
    return open(final_str+os.sep+path).read()