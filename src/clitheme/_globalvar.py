# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Global variable definitions for clitheme
"""

import io
import os
import sys
import re
import string
import stat
import tempfile
import ctypes
from copy import copy
from . import _version
from typing import List

# spell-checker:ignoreRegExp banphrase[s]{0,1}

error_msg_str= \
"""[CLItheme] Error: unable to get your home directory or invalid home directory information.
Please make sure that the {var} environment variable is set correctly.
Try restarting your terminal session to fix this issue."""

clitheme_version=_version.version_disp

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

clitheme_temp_root=tempfile.gettempdir()
# Function might return 'bytes' on older Python versions
if type(clitheme_temp_root)==bytes:
    clitheme_temp_root=clitheme_temp_root.decode('utf-8')

## _generator file and folder names
generator_info_pathname="theme-info" # e.g. ~/.local/share/clitheme/theme-info
generator_data_pathname="theme-data" # e.g. ~/.local/share/clitheme/theme-data
generator_manpage_pathname="manpages" # e.g. ~/.local/share/clitheme/manpages
generator_index_filename="current_theme_index" # e.g. [...]/theme-info/current_theme_index
generator_info_filename="clithemeinfo_{info}" # e.g. [...]/theme-info/1/clithemeinfo_name
generator_info_v2filename=generator_info_filename+"_v2" # e.g. [...]/theme-info/1/clithemeinfo_description_v2

## _generator.db_interface file and table names
db_data_tablename="clitheme_subst_data"
db_filename="subst-data.db" # e.g. ~/.local/share/clitheme/subst-data.db
db_version=5

## clitheme-exec timeout value for each output substitution operation
output_subst_timeout=0.4

## Sanity check function
entry_banphrases=['<', '>', ':', '"', '/', '\\', '|', '?', '*']
startswith_banphrases=['.']
banphrase_error_message="cannot contain '{char}'"
banphrase_error_message_orig=copy(banphrase_error_message)
startswith_error_message="cannot start with '{char}'"
startswith_error_message_orig=copy(startswith_error_message)
empty_error_message="cannot be empty"
empty_error_message_orig=copy(empty_error_message)
# function to check whether the pathname contains invalid phrases
# - cannot start with .
# - cannot contain banphrases
sanity_check_error_message=""
# retrieve the entry only once to avoid dead loop in frontend.FetchDescriptor callbacks
msg_retrieved=False
from . import frontend
def sanity_check(path: str, use_orig: bool=False) -> bool:
    # retrieve the entry (only for the first time)
    global msg_retrieved
    global sanity_check_error_message, banphrase_error_message, startswith_error_message, empty_error_message
    if not msg_retrieved and not use_orig:
        msg_retrieved=True
        f=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")
        banphrase_error_message=f.feof("sanity-check-msg-banphrase-err", banphrase_error_message, char="{char}")
        startswith_error_message=f.feof("sanity-check-msg-startswith-err", startswith_error_message, char="{char}")
        empty_error_message=f.reof("sanity-check-msg-empty-err", empty_error_message)
    global sanity_check_error_message
    if path.strip()=='':
        sanity_check_error_message=empty_error_message if not use_orig else empty_error_message_orig
        return False
    for p in path.split():
        for b in startswith_banphrases:
            if p.startswith(b):
                sanity_check_error_message=startswith_error_message.format(char=b) if not use_orig else startswith_error_message_orig.format(char=b)
                return False
        for b in entry_banphrases:
            if p.find(b)!=-1:
                sanity_check_error_message=banphrase_error_message.format(char=b) if not use_orig else banphrase_error_message_orig.format(char=b)
                return False
    return True

## Convenience functions

class _direct_exit(Exception):
    def __init__(self, code):
        """
        Custom exception for handling return code inside another function callback
        """
        self.code=code
def splitarray_to_string(split_content: List[str]) -> str:
    final=""
    for phrase in split_content:
        final+=phrase+" "
    return final.strip()
def extract_content(line_content: str, begin_phrase_count: int=1) -> str:
    results=re.search(r"(?:\s*.+?\s+){"+str(begin_phrase_count)+r"}(?P<content>.+)", line_content.strip())
    if results==None: raise ValueError("Match content failed (no matches)")
    else: return results.groupdict()['content']
def list_directory(dirname: str):
    lsdir_result=os.listdir(dirname)
    final_result=[]
    for name in lsdir_result:
        if not name.startswith('.'):
            final_result.append(name)
    return final_result
def make_printable(content: str) -> str:
    final_str=""
    for character in content:
        if character.isprintable() or character in string.whitespace: final_str+=character
        else:
            exp=repr(character)
            # Remove quotes in repr(character)
            exp=re.sub(r"""^(?P<quote>['"]?)(?P<content>.+)(?P=quote)$""", r"<\g<content>>", exp)
            final_str+=exp
    return final_str
def get_locale(debug_mode: bool=False) -> List[str]:
    lang=[]
    def add_language(target_lang: str):
        nonlocal lang
        if not sanity_check(target_lang, use_orig=True)==False:
            no_encoding=re.sub(r"^(?P<locale>.+)[\.].+$", r"\g<locale>", target_lang)
            if not target_lang in lang: lang.append(target_lang)
            if not no_encoding in lang: lang.append(no_encoding)
        else:
            if debug_mode: print("[Debug] Locale \"{0}\": sanity check failed ({1})".format(target_lang, sanity_check_error_message))

    # Skip $LANGUAGE if both $LANG and $LC_ALL is set to C (treat empty as C also)
    LANG_value=os.environ["LANG"] if "LANG" in os.environ and os.environ["LANG"].strip()!='' else "C"
    LC_ALL_value=os.environ["LC_ALL"] if "LC_ALL" in os.environ and os.environ["LC_ALL"].strip()!='' else "C"
    skip_LANGUAGE=(LANG_value=="C" or LANG_value.startswith("C.")) and (LC_ALL_value=="C" or LC_ALL_value.startswith("C."))
    # $LANGUAGE (list of languages separated by colons)
    if "LANGUAGE" in os.environ and os.environ["LANGUAGE"].strip()!="" and not skip_LANGUAGE:
        if debug_mode: print("[Debug] Using LANGUAGE variable")
        target_str=os.environ['LANGUAGE']
        for language in target_str.split(":"):
            each_language=language.strip()
            if each_language=="": continue
            # Ignore en and en_US (See https://wiki.archlinux.org/title/Locale#LANGUAGE:_fallback_locales)
            if each_language!="en" and each_language!="en_US":
                # Treat C as en_US also
                if re.sub(r"^(?P<locale>.+)[\.].+$", r"\g<locale>", each_language)=="C":
                    for item in ["en_US", "en"]:
                        with_encoding=re.subn(r"^.+[\.]", f"{item}.", each_language) # (content, num_of_substitutions)
                        if with_encoding[1]>0: add_language(with_encoding[0])
                        else: add_language(item)
                add_language(each_language)
    # $LC_ALL
    elif "LC_ALL" in os.environ and os.environ["LC_ALL"].strip()!="":
        if debug_mode: print("[Debug] Using LC_ALL variable")
        target_str=os.environ["LC_ALL"].strip()
        add_language(target_str)
    # $LANG
    elif "LANG" in os.environ and os.environ["LANG"].strip()!="":
        if debug_mode: print("[Debug] Using LANG variable")
        target_str=os.environ["LANG"].strip()
        add_language(target_str)

    if os.name=="nt":
        try:
            s=ctypes.create_unicode_buffer(85)
            assert ctypes.windll.kernel32.GetUserDefaultLocaleName(s, 85)!=0
            win_locale: str=s.value
        except: pass
        else:
            if win_locale.strip()!="":
                add_language(win_locale+".UTF-8")
                add_language(win_locale.replace('-','_')+".UTF-8")
    return lang

def handle_exception():
    env_var="CLITHEME_SHOW_TRACEBACK"
    if env_var in os.environ and os.environ[env_var]=="1":
        raise

def handle_stdin_prompt(path: str) -> bool:
    fi=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="cli apply-theme")
    is_stdin=False
    try:
        if os.stat(path).st_ino==os.stat(sys.stdin.fileno()).st_ino:
            is_stdin=True
            print("\n"+fi.reof("reading-stdin-note", "Reading from standard input"))
            if not stat.S_ISFIFO(os.stat(path).st_mode):
                print(fi.feof("stdin-interactive-finish-prompt", "Input file content here and press {shortcut} to finish", shortcut="CTRL-D" if os.name=="posix" else "CTRL-Z+<Enter>"))
    except: pass
    return is_stdin

def handle_set_themedef(fr: frontend, debug_name: str): # type: ignore
    prev_mode=False
    # Prevent interference with other code piping stdout
    orig_stdout=sys.stdout
    try:
        files=["strings/generator-strings.clithemedef.txt", "strings/cli-strings.clithemedef.txt", "strings/exec-strings.clithemedef.txt", "strings/man-strings.clithemedef.txt"]
        file_contents=list(map(lambda name: open(f"{os.path.dirname(__file__)}/{name}", encoding='utf-8').read(), files))
        msg=io.StringIO()
        sys.stdout=msg
        fr.set_debugmode(True)
        if not fr.set_local_themedefs(file_contents): raise RuntimeError("Full log below: \n"+msg.getvalue())
        fr.set_debugmode(prev_mode)
        sys.stdout=orig_stdout
    except:
        sys.stdout=orig_stdout
        fr.set_debugmode(prev_mode)
        # If pre-release build or manual environment variable flag set, display error
        if _version.release<0 or os.environ.get("CLITHEME_SHOW_TRACEBACK")=='1':
            print(f"{debug_name} set_local_themedef failed: "+str(sys.exc_info()[1]), file=sys.__stdout__)
            handle_exception()
    finally: sys.stdout=orig_stdout
def result_sort_cmp(obj1,obj2) -> int:
    cmp1='';cmp2=''
    try:
        cmp1=int(obj1); cmp2=int(obj2)
    except ValueError:
        cmp1=obj1; cmp2=obj2
    if cmp1>cmp2: return 1
    elif cmp1==cmp2: return 0
    else: return -1