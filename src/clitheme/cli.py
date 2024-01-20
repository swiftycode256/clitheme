#!/usr/bin/python3

"""
clitheme command line utility interface
"""

import os
import sys
import shutil
import re
try:
    from . import _globalvar
    from . import _generator
    from . import frontend
except ImportError:
    import _globalvar
    import _generator
    import frontend

usage_description=\
"""Usage: {0} apply-theme [themedef-file] [--overlay] [--preserve-temp]
       {0} get-current-theme-info
       {0} unset-current-theme
       {0} generate-data [themedef-file] [--overlay]
       {0} --help
       {0} --version"""

frontend.global_domain="swiftycode"
frontend.global_appname="clitheme"
frontend.global_subsections="cli"

def apply_theme(file_contents: list[str], overlay: bool, preserve_temp=False, generate_only=False):
    """
    Apply the theme using the provided definition file contents in a list[str] object.

    - Set overlay=True to overlay the theme on top of existing theme[s]
    - Set preserve_temp=True to preserve the temp directory (debugging purposes)
    - Set generate_only=True to generate the data hierarchy only (and not apply the theme)
    """
    f=frontend.FetchDescriptor(subsections="cli apply-theme")
    if overlay: print(f.reof("overlay-msg", "Overlay specified"))
    print(f.reof("generating-data", "==> Generating data..."))
    index=1
    generate_path=True
    if overlay:
        # Check if current data exists
        if not os.path.isfile(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename):
            print(f.reof("overlay-no-data", \
                "Error: no theme set or the current data is corrupt\nTry setting a theme first"))
            return 1
        # update index
        try: index=int(open(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename,'r', encoding="utf-8").read().strip())+1
        except ValueError:
            print(f.reof("overlay-data-error", \
                "Error: the current data is corrupt\nRemove the current theme, set the theme, and try again"))
            return 1
        # copy the current data into the temp directory
        _generator.generate_custom_path()
        shutil.copytree(_globalvar.clitheme_root_data_path, _generator.path)
        generate_path=False
    for i in range(len(file_contents)):
        if len(file_contents)>1: 
            print("    "+f.feof("processing-file", "> Processing file {filename}...", filename=str(i+1)))
        file_content=file_contents[i]
        # Generate data hierarchy, erase current data, copy it to data path
        try:
            _generator.generate_data_hierarchy(file_content, custom_path_gen=generate_path,custom_infofile_name=str(index))
            generate_path=False # Don't generate another temp folder after first one
            index+=1
        except SyntaxError:
            print(f.feof("generate-data-error", "[File {index}] An error occurred while generating the data:\n{message}", \
                index=str(i+1), message=str(sys.exc_info()[1]) ))
            return 1
    if len(file_contents)>1: 
        print("    "+f.reof("all-finished", "> All finished"))
    print(f.reof("generate-data-success", "Successfully generated data"))
    if preserve_temp or generate_only:
        if os.name=="nt":
            print(f.feof("view-temp-dir", "View at {path}", path=re.sub(r"/", r"\\", _generator.path))) # make the output look pretty
        else:
            print(f.feof("view-temp-dir", "View at {path}", path=_generator.path))
    if generate_only: return 0 
    # ---Stop here if generate_only is set---

    print(f.reof("applying-theme", "==> Applying theme..."))
    # remove the current data, ignoring directory not found error
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError: pass
    except Exception:
        print(f.feof("apply-theme-error", "An error occurred while applying the theme:\n{message}", message=str(sys.exc_info()[1])))
        return 1

    try:
        shutil.copytree(_generator.path, _globalvar.clitheme_root_data_path) 
    except Exception:
        print(f.feof("apply-theme-error", "An error occurred while applying the theme:\n{message}", message=str(sys.exc_info()[1])))
        return 1
    print(f.reof("apply-theme-success", "Theme applied successfully"))
    if not preserve_temp:
        try: shutil.rmtree(_generator.path)
        except Exception: pass
    return 0

def unset_current_theme():
    """
    Delete the current theme data hierarchy from the data path
    """
    f=frontend.FetchDescriptor(subsections="cli unset-current-theme")
    try: shutil.rmtree(_globalvar.clitheme_root_data_path)
    except FileNotFoundError:
        print(f.reof("no-data-found", "Error: No theme data present (no theme was set)"))
        return 1
    except Exception:
        print(f.feof("remove-data-error", "An error occurred while removing the data:\n{message}", message=str(sys.exc_info()[1])))
        return 1
    print(f.reof("remove-data-success", "Successfully removed the current theme data"))
    return 0

def get_current_theme_info():
    """
    Get the current theme info
    """
    f=frontend.FetchDescriptor(subsections="cli get-current-theme-info")
    search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
    if not os.path.isdir(search_path):
        print(f.reof("no-theme", "No theme currently set"))
        return 1
    lsdir_result=os.listdir(search_path)
    lsdir_result.sort(reverse=True) # sort by latest installed
    lsdir_num=0
    for x in lsdir_result: 
        if os.path.isdir(search_path+"/"+x):
            lsdir_num+=1
    if lsdir_num<=1: 
        print(f.reof("current-theme-msg", "Currently installed theme:"))
    else: 
        print(f.reof("overlay-history-msg", "Overlay history (sorted by latest installed):"))
    for theme_pathname in lsdir_result:
        target_path=search_path+"/"+theme_pathname
        if not os.path.isdir(target_path): continue # skip current_theme_index file
        # name
        name="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_name"):
            name=open(target_path+"/"+"clithemeinfo_name", 'r', encoding="utf-8").read().strip()
        print("[{}]: {}".format(theme_pathname, name))
        # version
        version="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_version"):
            version=open(target_path+"/"+"clithemeinfo_version", 'r', encoding="utf-8").read().strip()
            print(f.feof("version-str", "Version: {ver}", ver=version))
        # description
        description="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_description"):
            description=open(target_path+"/"+"clithemeinfo_description", 'r', encoding="utf-8").read()
            print(f.reof("description-str", "Description:"))
            print(description)
        # locales
        locales="(Unknown)"
        # version 2: items are separated by newlines instead of spaces
        if os.path.isfile(target_path+"/"+"clithemeinfo_locales_v2"):
            locales=open(target_path+"/"+"clithemeinfo_locales_v2", 'r', encoding="utf-8").read().strip()
            print(f.reof("locales-str", "Supported locales:"))
            for locale in locales.splitlines():
                if locale.strip()!="":
                    print(f.feof("list-item", "• {content}", content=locale.strip()))
        elif os.path.isfile(target_path+"/"+"clithemeinfo_locales"):
            locales=open(target_path+"/"+"clithemeinfo_locales", 'r', encoding="utf-8").read().strip()
            print(f.reof("locales-str", "Supported locales:"))
            for locale in locales.split():
                print(f.feof("list-item", "• {content}", content=locale.strip()))
        # supported_apps
        supported_apps="(Unknown)"
        if os.path.isfile(target_path+"/"+"clithemeinfo_supported_apps_v2"):
            supported_apps=open(target_path+"/"+"clithemeinfo_supported_apps_v2", 'r', encoding="utf-8").read().strip()
            print(f.reof("supported-apps-str", "Supported apps:"))
            for app in supported_apps.splitlines():
                if app.strip()!="":
                    print(f.feof("list-item", "• {content}", content=app.strip()))
        elif os.path.isfile(target_path+"/"+"clithemeinfo_supported_apps"):
            supported_apps=open(target_path+"/"+"clithemeinfo_supported_apps", 'r', encoding="utf-8").read().strip()
            print(f.reof("supported-apps-str", "Supported apps:"))
            for app in supported_apps.split():
                print(f.feof("list-item", "• {content}", content=app.strip()))
    return 0

def is_option(arg):
    return arg.strip()[0:1]=="-"
def handle_usage_error(message, cli_args_first):
    f=frontend.FetchDescriptor()
    print(message)
    print(f.feof("help-usage-prompt", "Run {clitheme} --help for usage information", clitheme=cli_args_first))
    return 1
def main(cli_args):
    """
    Use this function for indirect invocation of the interface (e.g. from another function)
    
    Provide a list of command line arguments to this function through cli_args.
    """
    f=frontend.FetchDescriptor()
    arg_first="clitheme" # controls what appears as the command name in messages
    if len(cli_args)<=1: # no arguments passed
        print(usage_description.format(arg_first))
        print(f.reof("no-command", "Error: no command or option specified"))
        return 1

    if cli_args[1]=="apply-theme" or cli_args[1]=="generate-data" or cli_args[1]=="generate-data-hierarchy":
        if len(cli_args)<3:
            return handle_usage_error(f.reof("not-enough-arguments", "Error: not enough arguments"), arg_first)
        generate_only=(cli_args[1]=="generate-data" or cli_args[1]=="generate-data-hierarchy")
        paths=[]
        overlay=False
        preserve_temp=False
        for arg in cli_args[2:]:
            if is_option(arg):
                if arg.strip()=="--overlay": overlay=True
                elif arg.strip()=="--preserve-temp" and not generate_only: preserve_temp=True
                else: return handle_usage_error(f.feof("unknown-option", "Error: unknown option \"{option}\"", option=arg), arg_first)
            else:
                paths.append(arg)
        fi=frontend.FetchDescriptor(subsections="cli apply-theme")
        if len(paths)>1 or True: # currently set to True for now
            if generate_only:
                print(fi.reof("generate-data-msg", "The theme data will be generated from the following definition files in the following order:"))
            else:
                print(fi.reof("apply-theme-msg", "The following definition files will be applied in the following order: "))
            for i in range(len(paths)):
                path=paths[i]
                print("\t{}: {}".format(str(i+1), path))
            if not generate_only:
                if os.path.isdir(_globalvar.clitheme_root_data_path) and overlay==False:
                    print(fi.reof("overwrite-notice", "The existing theme data will be overwritten if you continue."))
                if overlay==True:
                    print(fi.reof("overlay-notice", "The definition files will be appended on top of the existing theme data."))
                inpstr=fi.reof("confirm-prompt", "Do you want to continue? [y/n]")
                inp=input(inpstr+" ").strip().lower()
                if not (inp=="y" or inp=="yes"):
                    return 1
        content_list=[]
        for i in range(len(paths)):
            path=paths[i]
            try:
                content_list.append(open(path, 'r', encoding="utf-8").read())
            except Exception:
                print(fi.feof("read-file-error", "[File {index}] An error occurred while reading the file: \n{message}", \
                    index=str(i+1), message=str(sys.exc_info()[1])))
                return 1
        return apply_theme(content_list, overlay=overlay, preserve_temp=preserve_temp, generate_only=generate_only)
    elif cli_args[1]=="get-current-theme-info":
        if len(cli_args)>2: # disabled additional options
            return handle_usage_error(f.reof("too-many-arguments", "Error: too many arguments"), arg_first)
        return get_current_theme_info()
    elif cli_args[1]=="unset-current-theme":
        if len(cli_args)>2:
            return handle_usage_error(f.reof("too-many-arguments", "Error: too many arguments"), arg_first)
        return unset_current_theme()
    elif cli_args[1]=="--version":
        print(f.feof("version-str", "clitheme version {ver}", ver=_globalvar.clitheme_version))
    else:
        if cli_args[1]=="--help":
            print(usage_description.format(arg_first))
        else:
            return handle_usage_error(f.feof("unknown-command", "Error: unknown command \"{cmd}\"", cmd=cli_args[1]), arg_first)
    return 0
def script_main(): # for script
    exit(main(sys.argv))
if __name__=="__main__":
    exit(main(sys.argv))
