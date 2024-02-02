"""
Global variable definitions for clitheme
"""

import os
try: from . import _version
except ImportError: import _version

clitheme_root_data_path=""
if os.name=="posix": # Linux/macOS only
    try:
        clitheme_root_data_path=os.environ["XDG_DATA_HOME"]+"/clitheme"
    except KeyError: pass

error_msg_str= \
"""[clitheme] Error: unable to get your home directory or invalid home directory information.
Please make sure that the {var} environment variable is set correctly.
Try restarting your terminal session to fix this issue."""

if clitheme_root_data_path=="": # prev did not succeed
    try: 
        if os.name=="nt": # Windows
            clitheme_root_data_path=os.environ["USERPROFILE"]+"\\.local\\share\\clitheme"
        else:
            if not os.environ['HOME'].startswith('/'): # sanity check
                raise KeyError
            clitheme_root_data_path=os.environ["HOME"]+"/.local/share/clitheme"
    except KeyError:
        var="$HOME"
        if os.name=="nt":
            var=r"%USERPROFILE%"
        print(error_msg_str.format(var=var))
        exit(1)
clitheme_temp_root="/tmp"
if os.name=="nt":
    clitheme_temp_root=os.environ['TEMP']
clitheme_version=_version.__version__
generator_info_pathname="theme-info" # e.g. ~/.local/share/clitheme/theme-info
generator_data_pathname="theme-data" # e.g. ~/.local/share/clitheme/theme-data
generator_index_filename="current_theme_index"
entry_banphrases=['/','\\']
startswith_banphrases=['.']
banphrase_error_message="cannot contain '{char}'"
startswith_error_message="cannot start with '{char}'"
# function to check whether the pathname contains invalid phrases
# - cannot start with .
# - cannot contain banphrases
sanity_check_error_message=""

# retrieve the entry only once to avoid dead loop in frontend.FetchDescriptor callbacks
msg_retrieved=False
def sanity_check(path):
    # retrieve the entry (only for the first time)
    try: from . import frontend, _get_resource
    except ImportError: import frontend, _get_resource
    global msg_retrieved
    if not msg_retrieved:
        try:
            if not frontend.set_local_themedef(_get_resource.read_file("strings/generator-strings.clithemedef.txt")): raise RuntimeError()
        except:
            if _version.release==0: print("set_local_themedef failed")
            pass
        msg_retrieved=True
        f=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")
        global banphrase_error_message
        banphrase_error_message=f.feof("sanity-check-msg-banphrase-err", banphrase_error_message, char="{char}")
        global startswith_error_message
        startswith_error_message=f.feof("sanity-check-msg-startswith-err", startswith_error_message, char="{char}")
    global sanity_check_error_message
    for p in path.split():
        for b in startswith_banphrases:
            if p.startswith(b):
                sanity_check_error_message=startswith_error_message.format(char=b)
                return False
        for b in entry_banphrases:
            if p.find(b)!=-1:
                sanity_check_error_message=banphrase_error_message.format(char=b)
                return False
    return True
