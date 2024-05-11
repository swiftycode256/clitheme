#!/usr/bin/python3

"""
Module used for clitheme-man

- You can access clitheme-man by invoking this module directly: 'python3 -m clitheme.man'
- You can also invoke clitheme-man in scripts using the 'main' function
"""
import sys
import os
import subprocess
import shutil
try: from . import _globalvar
except ImportError: import _globalvar

def main(args: list[str]):
    """
    Invoke clitheme-man using the given command line arguments

    Note: the first item in the argument list must be the program name 
        (e.g. ['clitheme-man', <arguments>] or ['example-app', <arguments>])
    """
    if os.name=="nt":
        print("Windows platform not supported")
        return 1
    # check if "man" exists on system
    man_executable: str=shutil.which("man") # type: ignore
    if man_executable==None:
        print("Error: \"man\" is not installed on this system")
        return 1
    env=os.environ
    # check if theme is set
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.generator_manpage_pathname}"):
        print("Warning: no theme set or theme does not contain manpages")
    # set MANPATH
    env['MANPATH']=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_manpage_pathname+":"+(os.environ['MANPATH'] if 'MANPATH' in os.environ else '')
    # invoke man
    results=subprocess.run([man_executable]+args[1:], env=env)
    return results.returncode

def _script_main(): # for script
    return main(sys.argv)
if __name__=="__main__":
    exit(main(sys.argv))