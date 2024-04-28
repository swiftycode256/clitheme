"""
Module used for clitheme-exec (should not be invoked directly)
"""
import sys
import os
import io
import shutil
try:
    from . import output_handler_posix
    from .. import _globalvar, cli
    from .._generator import db_interface
except ImportError:
    import output_handler_posix
    import _globalvar, cli
    from _generator import db_interface

def check_regenerate_db() -> bool:
    try: db_interface.connect_db()
    except db_interface.need_db_regenerate:
        print("Migrating substrules database...")
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
            for pathname in lsdir_result:
                target_path=search_path+"/"+pathname
                if not os.path.isdir(target_path): continue
                content=open(target_path+"/file_content", encoding="utf-8").read()
                file_contents.append(content)
            cli_msg=io.StringIO()
            sys.stdout=cli_msg
            if not cli.apply_theme(file_contents, overlay=False, generate_only=True, preserve_temp=True)==0: 
                raise Exception("Failed to generate data (full log below):\n"+cli_msg.getvalue()+"\n")
            sys.stdout=sys.__stdout__
            os.remove(_globalvar.clitheme_root_data_path+"/"+_globalvar.db_filename)
            shutil.copy(cli._generator.path+"/"+_globalvar.db_filename, _globalvar.clitheme_root_data_path+"/"+_globalvar.db_filename)
            print("Successfully completed migration, proceeding execution")
        except:
            print("An error occurred while migrating the database: "+str(sys.exc_info()[1]))
            print("Please re-apply the theme and try again")
            return False
    except FileNotFoundError: pass
    except: 
        print("An error occurred while migrating the database: "+str(sys.exc_info()[1]))
        print("Please re-apply the theme and try again")
        return False
    return True

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
        else: print("Unknown option \"{}\"".format(arg)); return 1
    if not check_regenerate_db(): return 1
    # determine platform
    if os.name=="posix":
        return output_handler_posix.handler_main(arguments[1+argcount:], debug_mode)
    elif os.name=="nt":
        print("Windows platform is not currently supported")
        return 1
    else:
        print("Unsupported platform")
        return 1
    return 0