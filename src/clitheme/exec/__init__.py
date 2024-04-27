"""
Module used for clitheme-exec (should not be invoked directly)
"""
import sys
import os
try:
    from . import output_handler_posix
    from .. import _globalvar
except ImportError:
    import output_handler_posix
    import _globalvar
def main(arguments: list[str]):
    # get arguments
    if len(arguments)<2: 
        print("Not enough arguments")
        return 1
    # check database
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
        print("Warning: no theme set or theme does not have substrules")
    # process debug mode arguments
    debug_mode=[]
    argcount=0
    for arg in arguments[1:]:
        if not arg.startswith('-'): break
        argcount+=1
        if arg=="--debug":
            debug_mode.append("normal")
        elif arg=="--debug-color":
            debug_mode.append("color")
        elif arg=="--debug-newlines":
            debug_mode.append("newlines")
        elif arg=="--debug-showchars":
            debug_mode.append("showchars")
    # determine platform
    if os.name=="posix":
        output_handler_posix.handler_main(arguments[1+argcount:], debug_mode)
    elif os.name=="nt":
        print("Windows platform is not currently supported")
        return 1
    else:
        print("Unsupported platform")
        return 1
    return 0