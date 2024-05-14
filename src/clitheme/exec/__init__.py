"""
Module used for clitheme-exec

- You can access clitheme-exec by invoking this module directly: 'python3 -m clitheme.exec'
- You can also invoke clitheme-exec in scripts using the 'main' function
"""
import sys
import os
import io
import shutil
from . import output_handler_posix
from .. import _globalvar, cli, frontend
from .._generator import db_interface

_globalvar.handle_set_themedef(frontend, "clitheme-exec")
frontend.global_domain="swiftycode"
frontend.global_appname="clitheme"
fd=frontend.FetchDescriptor(subsections="exec")

def _check_regenerate_db() -> bool:
    try: db_interface.connect_db()
    except db_interface.need_db_regenerate:
        print(fd.reof("substrules-migrate-msg", "Migrating substrules database..."))
        try:
            # gather files
            search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
            if not os.path.isdir(search_path): raise Exception
            lsdir_result=os.listdir(search_path); lsdir_result.sort()
            lsdir_num=0
            for x in lsdir_result: 
                if os.path.isdir(search_path+"/"+x): lsdir_num+=1
            if lsdir_num<1: raise Exception

            file_contents=[]
            paths=[]
            for pathname in lsdir_result:
                target_path=search_path+"/"+pathname
                if not os.path.isdir(target_path): continue
                content=open(target_path+"/file_content", encoding="utf-8").read()
                file_contents.append(content)
                paths.append(target_path+"/manpage_data/file_content") # small hack/workaround
            cli_msg=io.StringIO()
            sys.stdout=cli_msg
            if not cli.apply_theme(file_contents, filenames=paths, overlay=False, generate_only=True, preserve_temp=True)==0: 
                raise Exception(fd.reof("db-migration-generator-err", "Failed to generate data (full log below):")+"\n"+cli_msg.getvalue()+"\n")
            sys.stdout=sys.__stdout__
            os.remove(_globalvar.clitheme_root_data_path+"/"+_globalvar.db_filename)
            shutil.copy(cli._generator.path+"/"+_globalvar.db_filename, _globalvar.clitheme_root_data_path+"/"+_globalvar.db_filename)
            print(fd.reof("db-migrate-success-msg", "Successfully completed migration, proceeding execution"))
        except:
            sys.stdout=sys.__stdout__
            print(fd.feof("db-migration-err", "An error occurred while migrating the database: {msg}\nPlease re-apply the theme and try again", msg=str(sys.exc_info()[1])))
            return False
    except FileNotFoundError: pass
    except: 
        print(fd.feof("db-migration-err", "An error occurred while migrating the database: {msg}\nPlease re-apply the theme and try again", msg=str(sys.exc_info()[1])))
        return False
    return True

def _handle_help_message(full_help: bool=False):
    fd2=frontend.FetchDescriptor(subsections="exec help-message")
    print(fd2.reof("usage-str", "Usage:"))
    print("\tclitheme-exec [--debug] [--debug-color] [--debug-newlines] [--debug-showchars] [command]")
    if not full_help: return
    print(fd2.reof("options-str", "Options:"))
    print("\t"+fd2.reof("options-debug", "--debug: Display indicator at the beginning of each read output by line"))
    print("\t"+fd2.reof("options-debug-color", "--debug-color: Apply color on output; used to determine stdout or stderr (BETA: stdout/stderr not implemented)"))
    print("\t"+fd2.reof("options-debug-newlines", "--debug-newlines: Use newlines to display output that does not end on a newline"))
    print("\t"+fd2.reof("options-debug-showchars", "--debug-showchars: Display various control characters in plain text"))

def _handle_error(message: str):
    print(message)
    print(fd.reof("help-usage-prompt", "Run \"clitheme-exec --help\" for usage information"))
    return 1

def main(arguments: list[str]):
    """
    Invoke clitheme-exec using the given command line arguments

    Note: the first item in the argument list must be the program name 
        (e.g. ['clitheme-exec', <arguments>] or ['example-app', <arguments>])
    """
    # process debug mode arguments
    debug_mode=[]
    argcount=0
    showhelp=False
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
        elif arg=="--help":
            showhelp=True
        else: 
            return _handle_error(fd.feof("unknown-option-err", "Error: unknown option \"{phrase}\"", phrase=arg))
    if len(arguments)<=1+argcount:
        if showhelp:
            _handle_help_message(full_help=True)
            return 0
        else: 
            _handle_help_message()
            _handle_error(fd.reof("no-command-err", "Error: no command specified"))
            return 1
    # check database
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
        print(fd.reof("no-theme-warn", "Warning: no theme set or theme does not have substrules"))
    if not _check_regenerate_db(): return 1
    # determine platform
    if os.name=="posix":
        return output_handler_posix._handler_main(arguments[1+argcount:], debug_mode)
    elif os.name=="nt":
        print("Error: Windows platform is not currently supported")
        return 1
    else:
        print("Error: Unsupported platform")
        return 1
    return 0
def _script_main(): # for script
    return main(sys.argv)