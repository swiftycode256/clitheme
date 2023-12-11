"""
Global variable definitions for clitheme
"""

import os
try: from . import _version
except ImportError: import _version

clitheme_root_data_path=""
try:
    clitheme_root_data_path=os.environ["XDG_DATA_HOME"]+"/clitheme"
except KeyError: None

if clitheme_root_data_path=="": # prev did not succeed
    try: 
        if not os.environ['HOME'].startswith("/"): # sanity check
            raise KeyError
        clitheme_root_data_path=os.environ["HOME"]+"/.local/share/clitheme"
    except KeyError:
        print("[clitheme] Error: unable to get your home directory or invaild home directory information")
        print("Please make sure that the $HOME environment variable is set correctly.")
        print("Try restarting your terminal session to fix this issue.")
        exit(1)
clitheme_temp_root="/tmp"
clitheme_version=_version.__version__
generator_info_pathname="theme-info" # e.g. ~/.local/share/clitheme/theme-info
generator_data_pathname="theme-data" # e.g. ~/.local/share/clitheme/theme-data
generator_index_filename="current_theme_index"
entry_banphrases=['/','\\']
# function to check whether the pathname contains invaild phrases
# - cannot start with .
# - cannot contain banphrases
sanity_check_error_message=""
def sanity_check(path):
    global sanity_check_error_message
    for p in path.split():
        if p.startswith('.'):
            sanity_check_error_message="cannot start with '.'"
            return False
        for b in entry_banphrases:
            if p.find(b)!=-1:
                sanity_check_error_message="cannot contain '{}'".format(b)
                return False
    return True