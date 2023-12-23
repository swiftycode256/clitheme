#!/usr/bin/python3

"""
clitheme command line utility interface
"""

import os
import sys
import shutil
try:
    from . import _globalvar
    from . import _generator
except ImportError:
    import _globalvar
    import _generator

usage_description=\
"""Usage: {0} apply-theme [themedef-file] [--overlay] [--preserve-temp]
       {0} get-current-theme-info
       {0} unset-current-theme
       {0} generate-data-hierarchy [themedef-file] [--overlay]
       {0} --help
       {0} --version"""

def apply_theme(file_content: str, overlay: bool, preserve_temp=False):
    """
    Apply the theme using the provided definition file content.

    - Set overlay=True to overlay the theme on top of existing theme[s]
    - Set preserve_temp=True to preserve the temp directory (debugging purposes)
    """
    if overlay: print("Overlay specified")
    print("==> Generating data...")
    index=1
    generate_path=True
    if overlay:
        # Check if current data exists
        if not os.path.isfile(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename):
            print("Error: no theme set or the current data is corrupt")
            print("Try setting a theme first")
            return 1
        # update index
        try: index=int(open(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename,'r').read().strip())+1
        except ValueError:
            print("Error: the current data is corrupt")
            print("Remove the current theme, set the theme, and try again")
            return 1
        # copy the current data into the temp directory
        _generator.generate_custom_path()
        shutil.copytree(_globalvar.clitheme_root_data_path, _generator.path)
        generate_path=False
    # Generate data hierarchy, erase current data, copy it to data path
    try:
        _generator.generate_data_hierarchy(file_content, custom_path_gen=generate_path,custom_infofile_name=str(index))
    except SyntaxError:
        print("An error occurred while generating the data:\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Successfully generated data")
    if preserve_temp:
        print("View at {}".format(_generator.path))
    print("==> Applying theme...")
    # remove the current data, ignoring directory not found error
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError: None
    try:
        shutil.copytree(_generator.path, _globalvar.clitheme_root_data_path) 
    except Exception:
        print("An error occurred while applying the theme:\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Theme applied successfully")
    if not preserve_temp:
        try: shutil.rmtree(_generator.path)
        except Exception: None
    return 0

def generate_data_hierarchy(file_content: str, overlay: bool):
    """
    Generate the data hierarchy at the temporary directory (debugging purposes only)
    """
    if overlay: print("Overlay specified")
    print("==> Generating data...")
    index=1
    generate_path=True
    if overlay:
        # Check if current data exists
        if not os.path.isfile(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename):
            print("Error: no theme set or the current data is corrupt")
            print("Try setting a theme first")
            return 1
        # update index
        try: index=int(open(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename,'r').read().strip())+1
        except ValueError:
            print("Error: the current data is corrupt")
            print("Remove the current theme, set the theme, and try again")
            return 1
        # copy the current data into the temp directory
        _generator.generate_custom_path()
        shutil.copytree(_globalvar.clitheme_root_data_path, _generator.path)
        generate_path=False
    # Generate data hierarchy, erase current data, copy it to data path
    try:
        _generator.generate_data_hierarchy(file_content, custom_path_gen=generate_path,custom_infofile_name=str(index))
    except SyntaxError:
        print("Error\nAn error occurred while generating the data:\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Successfully generated data")
    print("View at {}".format(_generator.path))
    return 0

def unset_current_theme():
    """
    Delete the current theme data hierarchy from the data path
    """
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError:
        print("No theme data present (no theme was set)")
        return 1
    except Exception:
        print("An error occurred while removing the data:\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Successfully removed the current theme data")
    return 0

def get_current_theme_info():
    """
    Get the current theme info
    """
    search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
    if not os.path.isdir(search_path):
        print("No theme currently set")
        return 1
    lsdir_result=os.listdir(search_path)
    lsdir_result.sort(reverse=True) # sort by latest installed
    lsdir_num=0
    for x in lsdir_result: 
        if os.path.isdir(search_path+"/"+x):
            lsdir_num+=1
    if lsdir_num<=1: print("Currently installed theme: ")
    else: print("Overlay history (sorted by latest installed):")
    for theme_pathname in lsdir_result:
        target_path=search_path+"/"+theme_pathname
        if not os.path.isdir(target_path): continue # skip current_theme_index file
        # name
        name="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_name"):
            name=open(target_path+"/"+"clithemeinfo_name", 'r').read().strip()
        print("[{}]: {}".format(theme_pathname, name))
        # version
        version="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_version"):
            version=open(target_path+"/"+"clithemeinfo_version", 'r').read().strip()
            print("Version: {}".format(version))
        # description
        description="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_description"):
            description=open(target_path+"/"+"clithemeinfo_description", 'r').read()
            print("Description:")
            print(description)
        # locales
        locales="(Unknown)"
        # version 2: items are seperated by newlines instead of spaces
        if os.path.isfile(target_path+"/"+"clithemeinfo_locales_v2"):
            locales=open(target_path+"/"+"clithemeinfo_locales_v2", 'r').read().strip()
            print("Supported locales:")
            for locale in locales.splitlines():
                if locale.strip()!="":
                    print("• {}".format(locale.strip()))
        elif os.path.isfile(target_path+"/"+"clithemeinfo_locales"):
            locales=open(target_path+"/"+"clithemeinfo_locales", 'r').read().strip()
            print("Supported locales: ")
            for locale in locales.split():
                print("• {}".format(locale))
        # supported_apps
        supported_apps="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_supported_apps_v2"):
            supported_apps=open(target_path+"/"+"clithemeinfo_supported_apps_v2", 'r').read().strip()
            print("Supported apps: ")
            for app in supported_apps.splitlines():
               if app.strip()!="":
                print("• {}".format(app))
        elif os.path.isfile(target_path+"/"+"clithemeinfo_supported_apps"):
            supported_apps=open(target_path+"/"+"clithemeinfo_supported_apps", 'r').read().strip()
            print("Supported apps: ")
            for app in supported_apps.split():
                print("• {}".format(app))
        print() # newline 
    return 0

def is_option(arg):
    return arg.strip()[0:1]=="-"
def handle_usage_error(message, cli_args_first):
    print(message)
    print("Run {0} --help for usage information".format(cli_args_first))
    return 1
def main(cli_args):
    """
    Use this function for indirect invocation of the interface (e.g. from another function)
    
    Provide a list of command line arguments to this function through cli_args.
    """
    arg_first="clitheme" # controls what appears as the command name in messages
    if len(cli_args)<=1: # no arguments passed
        print(usage_description.format(arg_first))
        print("Error: no command or option specified")
        return 1

    if cli_args[1]=="apply-theme":
        if len(cli_args)<3:
            return handle_usage_error("Error: not enough arguments", arg_first)
        path=""
        overlay=False
        preserve_temp=False
        for arg in cli_args[2:]:
            if is_option(arg):
                if arg.strip()=="--overlay": overlay=True
                elif arg.strip()=="--preserve-temp": preserve_temp=True
                else: return handle_usage_error("Unknown option \"{}\"".format(arg), arg_first)
            else:
                if path!="": # already specified path
                    return handle_usage_error("Error: too many arguments", arg_first)
                path=arg
        contents=""
        try:
            contents=open(path, 'r').read()
        except Exception:
            print("An error occurred while reading the file: \n{}".format(str(sys.exc_info()[1])))
            return 1
        return apply_theme(contents, overlay=overlay, preserve_temp=preserve_temp)
    elif cli_args[1]=="get-current-theme-info":
        if len(cli_args)>2: # disabled additional options
            return handle_usage_error("Error: too many arguments", arg_first)
        return get_current_theme_info()
    elif cli_args[1]=="unset-current-theme":
        if len(cli_args)>2:
            return handle_usage_error("Error: too many arguments", arg_first)
        return unset_current_theme()
    elif cli_args[1]=="generate-data-hierarchy":
        if len(cli_args)<3:
            return handle_usage_error("Error: not enough arguments", arg_first)
        path=""
        overlay=False
        for arg in cli_args[2:]:
            if is_option(arg):
                if arg.strip()=="--overlay": overlay=True
                else: return handle_usage_error("Unknown option \"{}\"".format(arg), arg_first)
            else:
                if path!="": # already specified path
                    return handle_usage_error("Error: too many arguments", arg_first)
                path=arg
        contents=""
        try:
            contents=open(path, 'r').read()
        except Exception:
            print("An error occurred while reading the file: \n{}".format(str(sys.exc_info()[1])))
            return 1
        return generate_data_hierarchy(contents, overlay=overlay)
    elif cli_args[1]=="--version":
        print("clitheme version {0}".format(_globalvar.clitheme_version))
    else:
        if cli_args[1]=="--help":
            print(usage_description.format(arg_first))
        else:
            return handle_usage_error("Error: unknown command \"{0}\"".format(cli_args[1]), arg_first)
    return 0
def script_main(): # for script
    exit(main(sys.argv))
if __name__=="__main__":
    exit(main(sys.argv))
