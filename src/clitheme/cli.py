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
"""Usage: {0} apply-theme [themedef-file] [--override (default)] [--preserve-temp]
       {0} get-current-theme-info
       {0} unset-current-theme
       {0} generate-data-hierarchy [themedef-file] [--parent-dir [parent directory]]
       {0} --help
       {0} --version"""

def apply_theme(file_content, override=True, preserve_temp=False):
    """
    Apply the theme using the provided definition file content.

    - Set override=False to overlay the theme on top of existing theme[s] (not implemented)
    - Set preserve_temp=True to preserve the temp directory (debugging purposes)
    """
    print("==> Generating data...")
    # Generator data hierarchy, erase current data, copy it to data path
    try:
        _generator.generate_data_hierarchy(file_content)
    except SyntaxError:
        print("Error\nAn error occurred while generating the data:\n\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Successfully generated data\n==> Applying theme...",end='')
    # remove the current data, ignoring directory not found
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError: None
    try:
        shutil.copytree(_generator.path, _globalvar.clitheme_root_data_path) 
    except Exception:
        print("Error\nAn error occurred while applying the theme:\n\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Success\nTheme applied successfully")
    if not preserve_temp:
        try: shutil.rmtree(_generator.path)
        except Exception: None
    return 0

def unset_current_theme():
    """
    Delete the current theme data hierarchy from the data path
    """
    print("==> Removing data...", end='')
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError:
        print("Error\nNo theme data present (no theme was set)")
        return 1
    except Exception:
        print("Error\nAn error occurred while removing the data:\n\n{}".format(str(sys.exc_info()[1])))
        return 1
    print("Success\nSuccessfully removed the current theme data")
    return 0

def get_current_theme_info(type):
    """
    Get the current theme info of the specified type (name,version,locales, or all)
    """
    search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
    if not os.path.isdir(search_path):
        print("No theme currently set")
        return 1
    lsdir_result=os.listdir(search_path)
    lsdir_result.sort(reverse=True) # sort by latest installed
    print("Currently installed themes (sorted by latest installed):")
    for theme_pathname in lsdir_result:
        target_path=search_path+"/"+theme_pathname
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
        # locales
        locales="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_locales"):
            locales=open(target_path+"/"+"clithemeinfo_locales", 'r').read().strip()
            print("Supported locales: {}".format(locales))
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
    if len(cli_args)<=1: # no arguments passed
        print(usage_description.format(cli_args[0]))
        print("Error: no command or option specified")
        return 1

    if cli_args[1]=="apply-theme":
        if len(cli_args)<3:
            return handle_usage_error("Error: not enough arguments", cli_args[0])
        path=""
        override=True # not yet implemented
        preserve_temp=False
        for arg in cli_args[2:]:
            if is_option(arg):
                if arg.strip()=="--override": override=True
                elif arg.strip()=="--preserve-temp": preserve_temp=True
                else: return handle_usage_error("Unknown option \"{}\"".format(arg), cli_args[0])
            else:
                if path!="": # already specified path
                    return handle_usage_error("Error: too many arguments", cli_args[0])
                path=arg
        return apply_theme(open(path, 'r').read(), override=override, preserve_temp=preserve_temp)
    elif cli_args[1]=="get-current-theme-info":
        if len(cli_args)>2: # disabled additional options
            return handle_usage_error("Error: too many arguments", cli_args[0])
        elif len(cli_args)<3:
            return get_current_theme_info("")
        elif cli_args[2]!="name" and cli_args[2]!="version" and cli_args[2]!="locales" and cli_args[2]!="all":
            return handle_usage_error("Error: invaild option \"{}\"".format(cli_args[2]), cli_args[0])
        return get_current_theme_info(cli_args[2])
    elif cli_args[1]=="unset-current-theme":
        if len(cli_args)>2:
            return handle_usage_error("Error: too many arguments", cli_args[0])
        return unset_current_theme()
    elif cli_args[1]=="generate-data-hierarchy":
        print("Not yet implemented")
    elif cli_args[1]=="--version":
        print("clitheme version {0}".format(_globalvar.clitheme_version))
    else:
        if cli_args[1]=="--help":
            print(usage_description.format(cli_args[0]))
        else:
            return handle_usage_error("Error: unknown command \"{0}\"".format(cli_args[1]), cli_args[0])
    return 0
def script_main(): # for script
    exit(main(sys.argv))
if __name__=="__main__":
    exit(main(sys.argv))