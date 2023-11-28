"""
Global variable definitions for clitheme
"""

import os

clitheme_root_data_path=""

try: 
    if not os.environ['HOME'].startswith("/"): # sanity check
        raise KeyError
    clitheme_root_data_path=os.environ["HOME"]+"/.local/share/clitheme"
except KeyError:
    print("Error: unable to get your home directory or invaild home directory information")
    print("Please make sure that the $HOME environment variable is set correctly.")
    print("Try restarting your terminal session to fix this issue.")
    exit(1)
clitheme_temp_root="/tmp"
clitheme_version="1.0-dev"
entry_banphrases=['/','\\']