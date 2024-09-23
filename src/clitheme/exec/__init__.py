# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Module used for clitheme-exec

- You can access clitheme-exec by invoking this module directly: 'python3 -m clitheme.exec'
- You can also invoke clitheme-exec in scripts using the 'main' function
"""
import sys
import os
import re
import io
import shutil
import functools
def _labeled_print(msg: str):
    print("[clitheme-exec] "+msg)

from .. import _globalvar, cli, frontend
from .._generator import db_interface
from typing import List

# spell-checker:ignore lsdir showhelp argcount nosubst

frontend.global_domain="swiftycode"
frontend.global_appname="clitheme"
fd=frontend.FetchDescriptor(subsections="exec")

# Prevent recursion dead loops and accurately simulate that regeneration is only triggered once
db_already_regenerated=False

def _check_regenerate_db(dest_root_path: str=_globalvar.clitheme_root_data_path) -> bool:
    global db_already_regenerated
    try:
        # Support environment variable flag to force db regeneration (debug purposes)
        if os.environ.get("CLITHEME_REGENERATE_DB")=="1" and not db_already_regenerated:
            db_already_regenerated=True
            raise db_interface.need_db_regenerate("Forced database regeneration with $CLITHEME_REGENERATE_DB=1")
        else: db_interface.connect_db()
    except db_interface.need_db_regenerate:
        _labeled_print(fd.reof("substrules-migrate-msg", "Migrating substrules database..."))
        orig_stdout=sys.stdout
        try:
            # gather files
            search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
            if not os.path.isdir(search_path): raise Exception(search_path+" not directory")
            lsdir_result=os.listdir(search_path); lsdir_result.sort(key=functools.cmp_to_key(_globalvar.result_sort_cmp))
            lsdir_num=0
            for x in lsdir_result: 
                if os.path.isdir(search_path+"/"+x): lsdir_num+=1
            if lsdir_num<1: raise Exception("empty directory")

            file_contents=[]
            paths=[]
            for pathname in lsdir_result:
                target_path=search_path+"/"+pathname
                if (not os.path.isdir(target_path)) or re.search(r"^\d+$", pathname.strip())==None: continue # skip current_theme_index file
                content=open(target_path+"/file_content", encoding="utf-8").read()
                file_contents.append(content)
                paths.append(target_path+"/manpage_data/file_content") # small hack/workaround
            cli_msg=io.StringIO()
            sys.stdout=cli_msg
            if not cli.apply_theme(file_contents, filenames=paths, overlay=False, generate_only=True, preserve_temp=True)==0: 
                raise Exception(fd.reof("db-migration-generator-err", "Failed to generate data (full log below):")+"\n"+cli_msg.getvalue()+"\n")
            sys.stdout=orig_stdout
            try: os.remove(dest_root_path+"/"+_globalvar.db_filename)
            except FileNotFoundError: raise
            shutil.copy(cli.last_data_path+"/"+_globalvar.db_filename, dest_root_path+"/"+_globalvar.db_filename)
            _labeled_print(fd.reof("db-migrate-success-msg", "Successfully completed migration, proceeding execution"))
        except:
            sys.stdout=orig_stdout
            _labeled_print(fd.feof("db-migration-err", "An error occurred while migrating the database: {msg}\nPlease re-apply the theme and try again", msg=str(sys.exc_info()[1])))
            _globalvar.handle_exception()
            return False
    except FileNotFoundError: pass
    except: 
        _labeled_print(fd.feof("db-migration-err", "An error occurred while migrating the database: {msg}\nPlease re-apply the theme and try again", msg=str(sys.exc_info()[1])))
        _globalvar.handle_exception()
        return False
    return True

def _handle_help_message(full_help: bool=False):
    fd2=frontend.FetchDescriptor(subsections="exec help-message")
    print(fd2.reof("usage-str", "Usage:"))
    print("\tclitheme-exec [--debug] [--debug-color] [--debug-newlines] [--showchars] [--foreground-stat] [--nosubst] [command]")
    if not full_help: return
    print(fd2.reof("options-str", "Options:"))
    print("\t"+fd2.reof("options-debug", "--debug: Display indicator at the beginning of each read output by line"))
    print("\t\t"+fd2.reof("options-debug-newlines", "--debug-newlines: Use newlines to display output that does not end on a newline"))
    print("\t"+fd2.reof("options-debug-color", "--debug-color: Apply color on output; used to determine stdout or stderr (BETA: stdout/stderr not implemented)"))
    print("\t"+fd2.reof("options-showchars", "--showchars: Display various control characters in plain text"))
    print("\t"+fd2.reof("options-foreground-stat", "--foreground-stat: Display message when the foreground status of the process changes (value of tcgetpgrp)"))
    print("\t"+fd2.reof("options-nosubst", "--nosubst: Do not perform any output substitutions even if a theme is set"))

def _handle_error(message: str):
    print(message)
    print(fd.reof("help-usage-prompt", "Run \"clitheme-exec --help\" for usage information"))
    return 1

def main(arguments: List[str]):
    """
    Invoke clitheme-exec using the given command line arguments

    Note: the first item in the argument list must be the program name 
        (e.g. ['clitheme-exec', <arguments>] or ['example-app', <arguments>])
    """
    # process debug mode arguments
    debug_mode=[]
    argcount=0
    showhelp=False
    subst=True
    for arg in arguments[1:]:
        if not arg.startswith('-'): break
        argcount+=1
        if arg=="--debug":
            debug_mode.append("normal")
        elif arg=="--debug-color":
            debug_mode.append("color")
        elif arg=="--debug-newlines":
            debug_mode.append("newlines")
        elif arg in ("--showchars", "--debug-showchars"):
            debug_mode.append("showchars")
        elif arg in ("--foreground-stat", "--debug-foreground"):
            debug_mode.append("foreground")
        elif arg in ("--nosubst", "--debug-nosubst"):
            subst=False
        elif arg=="--help":
            showhelp=True
        else: 
            return _handle_error(fd.feof("unknown-option-err", "Error: unknown option \"{phrase}\"", phrase=arg))
    if "newlines" in debug_mode and not "normal" in debug_mode:
        return _handle_error(fd.reof("debug-newlines-not-with-debug", "Error: \"--debug-newlines\" must be used with \"--debug\" option"))
    if len(arguments)<=1+argcount:
        if showhelp:
            _handle_help_message(full_help=True)
            return 0
        else: 
            _handle_help_message()
            return _handle_error(fd.reof("no-command-err", "Error: no command specified"))
    # check database
    if subst:
        if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
            _labeled_print(fd.reof("no-theme-warn", "Warning: no theme set or theme does not have substrules"))
        else: 
            if not _check_regenerate_db(): return 1
    # determine platform
    if os.name=="posix":
        from . import output_handler_posix
        return output_handler_posix.handler_main(arguments[1+argcount:], debug_mode, subst)
    elif os.name=="nt":
        _labeled_print("Error: Windows platform is not currently supported")
        return 1
    else:
        _labeled_print("Error: Unsupported platform")
        return 1
    return 0
def _script_main(): # for script
    return main(sys.argv)