#!/usr/bin/python3

"""
clitheme command line utility interface
Command line utility functions:
    - Apply theme with data hierarchy generator (overlay or overwrite)
    cli apply-theme [themedef-file] [--override (default)]
    - Query theme information
    cli get-theme-info [name|version|locales|all]
    - Delete/unset current theme
    cli unset-current-theme
    - Generate data hierarchy (debug purpose)
    cli generate-data-hierarchy [themedef-file] [--parent-dir [parent directory]]
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
       {0} get-theme-info [name|version|locales|all]
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
        print("Error\nAn error occurred while generating the data:\n\n{}".format(str(repr(sys.exception()))))
        return 1
    print("Successfully generated data\n==> Applying theme...",end='')
    # remove the current data, ignoring directory not found
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError: None
    try:
        shutil.copytree(_generator.path, _globalvar.clitheme_root_data_path) 
    except Exception:
        print("Error\nAn error occurred while applying the theme:\n\n{}".format(str(repr(sys.exception()))))
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
    print("==> ")
def is_option(arg):
    return arg.strip()[0:1]=="-"
def main(cli_args):
    """
    Use this function for indirect invocation of the interface (e.g. from another function)
    
    Provide a list of command line arguments to this function through cli_args.
    """
    if len(cli_args)<=1: # no arguments passed
        print(usage_description.format(cli_args[0]))
        return 1

    if cli_args[1]=="apply-theme":
        if len(cli_args)<3:
            print("Not enough arguments")
            return 1
        path=""
        override=True # not yet implemented
        preserve_temp=False
        for arg in cli_args[2:]:
            if is_option(arg):
                if arg.strip()=="--override": override=True
                elif arg.strip()=="--preserve-temp": preserve_temp=True
                else: print("Unknown option \"{}\"".format(arg)); return 1
            else:
                if path!="": # already specified path
                    print("Error: too many arguments"); return 1
                path=arg
        return apply_theme(open(path, 'r').read(), override=override, preserve_temp=preserve_temp)
    elif cli_args[1]=="get-theme-info":
        print("Not yet implemented")
    elif cli_args[1]=="unset-current-theme":
        print("Not yet implemented")
    elif cli_args[1]=="generate-data-hierarchy":
        print("Not yet implemented")
    elif cli_args[1]=="--version":
        print("clitheme version {0}".format(_globalvar.clitheme_version))
    else:
        print(usage_description.format(cli_args[0]))
        if cli_args[1]!="--help":
            print("Error: unknown command \"{0}\"".format(cli_args[1]))
            return 1
    return 0
if __name__=="__main__":
    exit(main(sys.argv))