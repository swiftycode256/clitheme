"""
Global variable definitions for clitheme
"""

import os
import re
from copy import copy
try: from . import _version
except ImportError: import _version

error_msg_str= \
"""[clitheme] Error: unable to get your home directory or invalid home directory information.
Please make sure that the {var} environment variable is set correctly.
Try restarting your terminal session to fix this issue."""

clitheme_version=_version.__version__

## Core data paths
clitheme_root_data_path=""
if os.name=="posix": # Linux/macOS only: Try to get XDG_DATA_HOME if possible
    try:
        clitheme_root_data_path=os.environ["XDG_DATA_HOME"]+"/clitheme"
    except KeyError: pass

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
clitheme_temp_root="/tmp" if os.name!="nt" else os.environ['TEMP']

## _generator file and folder names
generator_info_pathname="theme-info" # e.g. ~/.local/share/clitheme/theme-info
generator_data_pathname="theme-data" # e.g. ~/.local/share/clitheme/theme-data
generator_index_filename="current_theme_index" # e.g. [...]/theme-info/current_theme_index
generator_info_filename="clithemeinfo_{info}" # e.g. [...]/theme-info/1/clithemeinfo_name
generator_info_v2filename=generator_info_filename+"_v2" # e.g. [...]/theme-info/1/clithemeinfo_description_v2

## _generator.db_interface file and table names
db_data_tablename="clitheme_subst_data"
db_filename="subst-data.db"

## Sanity check function
entry_banphrases=['/','\\']
startswith_banphrases=['.']
banphrase_error_message="cannot contain '{char}'"
banphrase_error_message_orig=copy(banphrase_error_message)
startswith_error_message="cannot start with '{char}'"
startswith_error_message_orig=copy(startswith_error_message)
# function to check whether the pathname contains invalid phrases
# - cannot start with .
# - cannot contain banphrases
sanity_check_error_message=""
# retrieve the entry only once to avoid dead loop in frontend.FetchDescriptor callbacks
msg_retrieved=False
try: from . import frontend, _get_resource
except ImportError: import frontend, _get_resource
def sanity_check(path: str, use_orig: bool=False) -> bool:
    def retrieve_entry():
        # retrieve the entry (only for the first time)
        global msg_retrieved
        global sanity_check_error_message, banphrase_error_message, startswith_error_message
        if not msg_retrieved:
            try:
                if not frontend.set_local_themedef(_get_resource.read_file("strings/generator-strings.clithemedef.txt")): raise RuntimeError()
                if not frontend.set_local_themedef(_get_resource.read_file("strings/cli-strings.clithemedef.txt"), overlay=True): raise RuntimeError()
            except RuntimeError:
                if _version.release==0: print("_globalvar set_local_themedef failed")
                pass
            msg_retrieved=True
            f=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")
            banphrase_error_message=f.feof("sanity-check-msg-banphrase-err", banphrase_error_message, char="{char}")
            startswith_error_message=f.feof("sanity-check-msg-startswith-err", startswith_error_message, char="{char}")
    global sanity_check_error_message
    for p in path.split():
        for b in startswith_banphrases:
            if p.startswith(b):
                if not use_orig: retrieve_entry()
                sanity_check_error_message=startswith_error_message.format(char=b) if not use_orig else startswith_error_message_orig.format(char=b)
                return False
        for b in entry_banphrases:
            if p.find(b)!=-1:
                if not use_orig: retrieve_entry()
                sanity_check_error_message=banphrase_error_message.format(char=b) if not use_orig else banphrase_error_message_orig.format(char=b)
                return False
    return True

## Convenience functions
def splitarray_to_string(split_content):
    final=""
    for phrase in split_content:
        final+=phrase+" "
    return final.strip()
def get_locale(debug_mode: bool=False):
    lang=[]
    # Skip $LANGUAGE if both $LANG and $LC_ALL is set to C (treat empty as C also)
    skip_LANGUAGE=False
    LANG_value=os.environ["LANG"] if "LANG" in os.environ and os.environ["LANG"].strip()!='' else "C"
    LC_ALL_value=os.environ["LC_ALL"] if "LC_ALL" in os.environ and os.environ["LC_ALL"].strip()!='' else "C"
    if (LANG_value=="C" or LANG_value.startswith("C.")) and (LC_ALL_value=="C" or LC_ALL_value.startswith("C.")): skip_LANGUAGE=True
    # $LANGUAGE (list of languages separated by colons)
    if "LANGUAGE" in os.environ and not skip_LANGUAGE:
        target_str=os.environ['LANGUAGE']
        for language in target_str.split(":"):
            each_language=language.strip()
            if each_language=="": continue
            # avoid exploit of accessing top-level folders
            if sanity_check(each_language)==False: continue
            # Ignore en and en_US (See https://wiki.archlinux.org/title/Locale#LANGUAGE:_fallback_locales)
            if each_language!="en" and each_language!="en_US":
                # Treat C as en_US also
                if re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", each_language)=="C":
                    lang.append(re.sub(r".+[\.]", "en_US.", each_language))
                    lang.append("en_US")
                lang.append(each_language)
                # no encoding
                lang.append(re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", each_language))
    # $LC_ALL
    elif "LC_ALL" in os.environ and os.environ["LC_ALL"].strip()!="":
        target_str=os.environ["LC_ALL"].strip()
        if not sanity_check(target_str, use_orig=True)==False:
            lang.append(target_str)
            lang.append(re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str))
        else:
            if debug_mode: print("[Debug] Locale: sanity check failed ({})".format(sanity_check_error_message))
    # $LANG
    elif "LANG" in os.environ and os.environ["LANG"].strip()!="":
        target_str=os.environ["LANG"].strip()
        if not sanity_check(target_str, use_orig=True)==False:
            lang.append(target_str)
            lang.append(re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str))
        else:
            if debug_mode: print("[Debug] Locale: sanity check failed ({})".format(sanity_check_error_message))
    return lang