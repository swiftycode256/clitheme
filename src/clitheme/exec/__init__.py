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
    # check dataase
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
        print("No theme set; please set a theme")
        return 1
    # determine platform
    if os.name=="posix":
        output_handler_posix.handler_main(arguments[1:])
    elif os.name=="nt":
        print("Windows platform is not currently supported")
        return 1
    else:
        print("Unsupported platform")
        return 1
    return 0