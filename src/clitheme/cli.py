# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Module used for the CLItheme command line interface

- You can access 'clitheme' by invoking this module directly: 'python3 -m clitheme'
- You can invoke individual commands in scripts using the functions in this module
"""

import os
import sys
import shutil
import re
import signal
import functools
from . import _globalvar, _frontend_internal as frontend
from ._globalvar import make_printable as fmt # A shorter alias of the function
from ._globalvar import direct_exit
from typing import List, Optional, Tuple

# spell-checker:ignore lsdir inpstr

frontend.set_domain(_globalvar.fd_domain_name)
frontend.set_appname(_globalvar.fd_app_name)
frontend.set_subsections("cli")

last_data_path=""
def apply_theme(file_contents: Optional[List[str]], filenames: List[str], overlay: bool=False, preserve_temp=False, generate_only=False, no_confirm=False):
    """
    Apply the theme using the provided definition file contents and file pathnames in a list object. 
    
    (Invokes 'clitheme apply-theme')

    - Set file_contents=None to read file contents from specified filenames
    - Set overlay=True to overlay the theme on top of existing theme[s]
    - Set preserve_temp=True to preserve the temp directory (debugging purposes)
    - Set generate_only=True to generate the data hierarchy only (invokes 'clitheme generate-data' instead)
    - Set no_confirm=True to skip displaying the file list and confirmation prompt
    """
    if file_contents==None:
        try: file_contents=_get_file_contents(filenames)
        except direct_exit as exc: return exc.code
    if len(filenames)==0:
        raise ValueError("Empty filenames array")
    if len(file_contents)!=len(filenames):
        raise ValueError("file_contents and filenames have different lengths")
    f=frontend.FetchDescriptor(subsections="cli apply-theme")
    if not no_confirm:
        # Display information and confirmation prompt
        if generate_only:
            print(f.reof("generate-data-msg", "The theme data will be generated from the following definition files in the following order:"))
        else:
            print(f.reof("apply-theme-msg", "The following definition files will be applied in the following order: "))
        for i in range(len(filenames)):
            path=filenames[i]
            print("\t{}: {}".format(str(i+1), fmt(path)))
        if not generate_only:
            if os.path.isdir(_globalvar.clitheme_root_data_path) and overlay==False:
                print(f.reof("overwrite-notice", "The existing theme data will be overwritten if you continue."))
            if overlay:
                print(f.reof("overlay-notice", "The definition files will be appended on top of the existing theme data."))
            inpstr=f.reof("confirm-prompt", "Do you want to continue? [y/n]")
            inp=input(inpstr+" ").strip().lower()
            if not (inp=="y" or inp=="yes"):
                return 1
    if overlay and no_confirm: print(f.reof("overlay-msg", "Overlay specified"))
    ## Process files and generate data
    from . import _generator
    index=1
    final_path=_generator.generate_custom_path()
    if overlay:
        # Check if current data exists
        if not os.path.isfile(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename):
            print(f.reof("overlay-no-data", \
                "Error: no theme set or the current data is corrupt\nTry setting a theme first"))
            return 1
        # Get current index
        try: index=int(_globalvar.read_file(_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename).strip())+1
        except ValueError:
            print(f.reof("overlay-data-error", \
                "Error: the current data is corrupt\nRemove the current theme, set the theme, and try again"))
            _globalvar.handle_exception()
            return 1
        # copy the current data into the temp directory
        shutil.copytree(_globalvar.clitheme_root_data_path, _generator.path)
    line_prefix=f"\x1b[2K\r" # clear current line content and move cursor to beginning
    orig_stdout=sys.stdout # Prevent interference with other code piping stdout
    err_count=0
    for i in range(len(file_contents)):
        print(line_prefix+f.feof("processing-file", "> Processing file {filename}...", filename=f"({i+1}/{len(file_contents)})"), end='', flush=True)
        file_content=file_contents[i]
        # Generate data hierarchy, erase current data, copy it to data path
        try:
            # Output the warning messages correctly (make sure that they start on new line if any exists)
            return_val=_generator.generate_data_hierarchy(file_content, custom_path_gen=False,custom_infofile_name=str(index), filename=filenames[i] if len(filenames)>0 else "")
            index+=1
            if len(return_val.messages)>0:
                print()
                print("\n".join(return_val.messages))
            if not return_val.success: err_count+=1
            assert return_val.dir_path==final_path, "Data path not the same"
        except:
            sys.stdout=orig_stdout
            print()
            print(f.feof("process-files-error", "[File {index}] An error occurred while processing the file:\n{message}", \
                index=str(i+1), message=fmt(str(sys.exc_info()[1]))))
            raise
    print(line_prefix, end='')
    if err_count>0:
        print(f.feof("files-contain-error","==> Errors detected in {count} file(s)", count=err_count))
        try:
            # Remove the temp directory
            assert final_path.startswith(_globalvar.clitheme_temp_root)
            shutil.rmtree(final_path)
        except: pass
        return 1
    else: print(f.reof("process-files-success", "==> Successfully processed files"))
    global last_data_path; last_data_path=final_path
    if preserve_temp or generate_only:
        if os.name=="nt":
            print(f.feof("view-temp-dir", "View at {path}", path=fmt(re.sub(r"/", r"\\", final_path)))) # make the output look pretty
        else:
            print(f.feof("view-temp-dir", "View at {path}", path=fmt(final_path)))
    if generate_only: return 0 
    # ---Stop here if generate_only is set---

    success_msg=f.reof("apply-theme-success", "Theme applied successfully")
    ## Apply theme: move generated folder to data directory
    try:
        if os.path.exists(_globalvar.clitheme_root_data_path):
            # remove the current data, ignoring directory not found error
            try: shutil.rmtree(_globalvar.clitheme_root_data_path)
            except: raise OSError(f"rmtree: {sys.exc_info()[1]}")
        else:
            # Create intermediate directories
            try: os.makedirs(os.path.dirname(_globalvar.clitheme_root_data_path), exist_ok=True)
            except: raise OSError(f"makedirs: {sys.exc_info()[1]}")
        if preserve_temp:
            shutil.copytree(final_path, _globalvar.clitheme_root_data_path) 
        else:
            assert not os.path.exists(_globalvar.clitheme_root_data_path), \
                f"Path exists after rmtree: {_globalvar.clitheme_root_data_path}"
            shutil.move(final_path, _globalvar.clitheme_root_data_path) 
    except:
        print(f.feof("apply-theme-error", "An error occurred while applying the theme:\n{message}", message=fmt(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    print(success_msg)
    return 0

def remove_theme(no_confirm=False):
    """
    Delete the current theme data hierarchy from the data path

    - Set no_confirm=True to skip the confirmation prompt

    (Invokes 'clitheme remove-theme')
    """
    f=frontend.FetchDescriptor(subsections="cli remove-theme")
    try: _fetch_abs_lsdir()
    except _invalid_theme:
        print(f.reof("no-theme-err", "Error: no theme currently set"))
        return 1
    
    if no_confirm: proceed=True
    else:
        # Display names of currently applied themes
        show_info(name=True)
        inpstr=f.reof("confirm-prompt", "Do you want to remove the theme(s)? [y/n]")
        proceed=input(inpstr+" ").strip().lower() in ('y', 'yes')
    if proceed:
        try:
            shutil.rmtree(_globalvar.clitheme_root_data_path)
        except:
            print(f.feof("remove-data-error", "An error occurred while removing the data:\n{message}", message=fmt(str(sys.exc_info()[1]))))
            _globalvar.handle_exception()
            return 1
        else:
            print(f.reof("remove-data-success", "Successfully removed the current theme data"))
            return 0
    else: return 1
unset_current_theme=remove_theme

def show_info(name: bool=False, file_path=False):
    """
    Displays the current theme info

    - Set name=True to only display the name of each theme
    - Set file_path=True to only display the source file path of each theme
    - Both information are displayed when both options are set to True

    (Invokes 'clitheme show-info')
    """
    f=frontend.FetchDescriptor(subsections="cli show-info")
    try: lsdir_result=_fetch_abs_lsdir()
    except _invalid_theme:
        print(f.reof("no-theme", "No theme currently set"))
        return 1
    print(f.reof("current-theme-msg", "Currently installed theme(s):"))
    minimal_info: bool=name==True or file_path==True
    for target_path in lsdir_result:
        # name
        if minimal_info==False or (minimal_info==True and name==True):
            theme_name="(Unknown)"
            if os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="name")):
                theme_name=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="name")).strip()
            print("[{}]: {}".format(os.path.basename(target_path), fmt(theme_name)))
        if minimal_info==True and file_path==True:
            theme_filepath="(Unknown)"
            if os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="filepath")):
                theme_filepath=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="filepath")).strip()
            print(fmt(theme_filepath))
        if minimal_info==True: continue # --Stop here if either parameters are specified--
        # version
        version="(Unknown)"
        if os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="version")):
            version=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="version")).strip()
            print(f.feof("version-str", "Version: {ver}", ver=fmt(version)))
        # description
        description="(Unknown)"
        if os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="description")):
            description=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="description"))
            print(f.reof("description-str", "Description:"))
            print(re.sub(r"\n\Z", "", fmt(description))) # remove the extra newline added by _generator
        # locales
        locales="(Unknown)"
        # version 2: items are separated by newlines instead of spaces
        if os.path.isfile(target_path+"/"+_globalvar.generator_info_v2filename.format(info="locales")):
            locales=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_v2filename.format(info="locales")).strip()
            print(f.reof("locales-str", "Supported locales:"))
            for locale in locales.splitlines():
                if locale.strip()!="":
                    print(f.feof("list-item", "• {content}", content=fmt(locale.strip())))
        elif os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="locales")):
            locales=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="locales")).strip()
            print(f.reof("locales-str", "Supported locales:"))
            for locale in locales.split():
                print(f.feof("list-item", "• {content}", content=fmt(locale.strip())))
        # supported_apps
        supported_apps="(Unknown)"
        if os.path.isfile(target_path+"/"+_globalvar.generator_info_v2filename.format(info="supported_apps")):
            supported_apps=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_v2filename.format(info="supported_apps")).strip()
            print(f.reof("supported-apps-str", "Supported apps:"))
            for app in supported_apps.splitlines():
                if app.strip()!="":
                    print(f.feof("list-item", "• {content}", content=fmt(app.strip())))
        elif os.path.isfile(target_path+"/"+_globalvar.generator_info_filename.format(info="supported_apps")):
            supported_apps=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="supported_apps")).strip()
            print(f.reof("supported-apps-str", "Supported apps:"))
            for app in supported_apps.split():
                print(f.feof("list-item", "• {content}", content=fmt(app.strip())))

        print() # Separate each entry with an empty line
    return 0
get_current_theme_info=show_info

class _invalid_theme(Exception): 
    def __init__(self, message: str):
        self.message=message
_is_not_datadir=lambda target_path: \
    (not os.path.isdir(target_path)) or re.search(r"^\d+$", os.path.basename(target_path))==None
def _fetch_abs_lsdir() -> List[str]:
    search_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_info_pathname
    if not os.path.isdir(search_path): 
        raise _invalid_theme("no theme set")
    lsdir_result=_globalvar.list_directory(search_path)
    lsdir_result.sort(key=functools.cmp_to_key(_globalvar.result_sort_cmp))
    # Make absolute path
    lsdir_result=list(map(lambda name:search_path+"/"+name, lsdir_result))
    lsdir_num=0
    lsdir_final=[]
    for target_path in lsdir_result: 
        if os.path.isdir(target_path): lsdir_num+=1
        # Don't include current_theme_index file
        if not _is_not_datadir(target_path): lsdir_final.append(target_path)
    if lsdir_num<1: raise _invalid_theme("empty directory")
    return lsdir_final

def _fetch_theme_data(get_filepath=True, get_file_contents=True) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    lsdir_result=_fetch_abs_lsdir()
    # Get file paths from clithemeinfo_filepath files
    file_paths: List[str]=[]
    # Get file contents from file_content files
    file_contents: List[str]=[]
    for target_path in lsdir_result:
        got_path: str
        try:
            if get_filepath:
                got_path=_globalvar.read_file(target_path+"/"+_globalvar.generator_info_filename.format(info="filepath")).strip()
                file_paths.append(got_path)
            if get_file_contents:
                content=_globalvar.read_file(target_path+"/file_content")
                file_contents.append(content)
        except: raise _invalid_theme("Read error: "+str(sys.exc_info()[1]))
    return (file_paths if get_filepath else None, file_contents if get_file_contents else None)

def update_theme(no_confirm=False, preserve_temp=False):
    """
    Re-applies theme files from file paths specified in the previous apply-theme command (including all related apply-theme commands if --overlay is used)

    - Set no_confirm=True to skip the user confirmation prompt

    (Invokes 'clitheme update-theme')
    """
    fi=frontend.FetchDescriptor(subsections="cli update-theme")
    try:
        file_paths: List[str]=_fetch_theme_data(get_filepath=True, get_file_contents=False)[0] # type: ignore
    except _invalid_theme as exc:
        if exc.message=="no theme set":
            print(fi.reof("no-theme-err", "Error: no theme currently set"))
        else:
            print(fi.reof("not-available-err", "update-theme cannot be used with the current theme setting\nPlease re-apply the current theme and try again"))
            _globalvar.handle_exception()
        return 1
    except:
        print(fi.feof("other-err", "An error occurred while processing file path information: {msg}\nPlease re-apply the current theme and try again", msg=fmt(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    return apply_theme(None, file_paths, overlay=False, preserve_temp=preserve_temp, no_confirm=no_confirm)

def repair_theme():
    """
    Re-applies theme files stored in the current theme data

    (Invokes `clitheme repair-theme`)
    """
    fi=frontend.FetchDescriptor(subsections="cli repair-theme")
    # Get file paths and file contents
    try:
        file_paths: List[str]
        file_contents: List[str]
        file_paths, file_contents=_fetch_theme_data(get_filepath=True, get_file_contents=True) # type: ignore
    except _invalid_theme as exc:
        if exc.message=="no theme set":
            print(fi.reof("no-theme-err", "Error: no theme currently set"))
        else:
            print(fi.reof("not-available-err", "repair-theme cannot be used with the current theme setting\nPlease re-apply the current theme and try again"))
            _globalvar.handle_exception()
        return 1
    except:
        print(fi.feof("other-err", "An error occurred: {msg}\nPlease re-apply the current theme and try again", msg=fmt(str(sys.exc_info()[1]))))
        _globalvar.handle_exception()
        return 1
    lsdir_result=_fetch_abs_lsdir()
    assert len(lsdir_result)==len(file_paths), f"{len(lsdir_result)}!={len(file_paths)}"
    # Run apply-theme to overwrite existing data
    # Quick workaround to handle manpage paths in definition files
    apply_paths=list(map(lambda path: path+"/manpage_data/file_content", lsdir_result))
    if apply_theme(file_contents, apply_paths, no_confirm=True)!=0: return 1
    # Replace filepath theme-info data
    try:
        for x in range(len(lsdir_result)):
            target_path=lsdir_result[x]
            info_path=target_path+"/"+_globalvar.generator_info_filename.format(info="filepath")
            _globalvar.write_file(info_path, file_paths[x]+"\n")
    except Exception as exc:
        print(fi.feof("other-err", "An error occurred: {msg}\nPlease re-apply the current theme and try again", msg=fmt(str(sys.exc_info()[1]))))
        return 1
    return 0

def _is_option(arg):
    return arg.strip()[0:1]=="-"
def _handle_usage_error(message, cli_args_first):
    f=frontend.FetchDescriptor()
    print(message)
    print(f.feof("help-usage-prompt", "Run \"{clitheme} --help\" for usage information", clitheme=cli_args_first))
    return 1
arg_first="clitheme" # controls what appears as the command name in messages
def _handle_help_message(full_help: bool=False):
    fd=frontend.FetchDescriptor(subsections="cli help-message")
    print(fd.reof("usage-str", "Usage:"))
    print(
"""\t{0} apply-theme [file] (--overlay) (--preserve-temp) (--yes)
\t{0} update-theme (--yes) (--preserve-temp)
\t{0} show-info (--name) (--file-path)
\t{0} remove-theme (--yes)
\t{0} generate-data [file] (--overlay)
\t{0} repair-theme
\t{0} --version
\t{0} --help""".format(arg_first)
    )
    if not full_help: return
    print(fd.reof("options-str", "Options:"))
    print("\t"+fd.reof("options-apply-theme",
        "apply-theme: Apply the given theme definition file(s).\n"
        "Specify --overlay to add file(s) onto the current data.\n"
        "Specify --preserve-temp to preserve the temporary directory after the operation. (Debug purposes only)").replace("\n", "\n\t\t"))
    print("\t"+fd.reof("options-update-theme.2",
        "update-theme: Re-apply the theme definition files specified in previous \"apply-theme\" commands\n"
        "Specify --preserve-temp to preserve the temporary directory after the operation. (Debug purposes only)").replace("\n", "\n\t\t"))
    print("\t"+fd.reof("options-show-info",
        "show-info: Show information about the currently applied theme(s)\n"
        "Specify --name to only display the name of each theme\n"
        "Specify --file-path to only display the source file path of each theme\n"
        "(Both will be displayed when both specified)").replace("\n", "\n\t\t"))
    print("\t"+fd.reof("options-remove-theme",
        "remove-theme: Remove the current theme data from the system"))
    print("\t"+fd.reof("options-generate-data",
        "generate-data: [Debug purposes only] Generate a data hierarchy from specified theme definition files in a temporary directory"))
    print("\t"+fd.reof("options-repair-theme",
        "repair-theme: [Debug purposes only] Re-apply theme from stored theme definition files in current data"))
    print("\t"+fd.reof("options-yes",
        "[For supported commands, specify --yes to skip the confirmation prompt]"))
    print("\t"+fd.reof("options-version", "--version: Show the current version of clitheme"))
    print("\t"+fd.reof("options-help", "--help: Show this help message"))

def _get_file_contents(file_paths: List[str]) -> List[str]:
    fi=frontend.FetchDescriptor(subsections="cli apply-theme")
    content_list=[]
    line_prefix="\x1b[2K\r" # clear current line content and move cursor to beginning
    has_error=False
    for i in range(len(file_paths)):
        path=file_paths[i]
        try:
            print(line_prefix+fi.feof("reading-file","> Reading file {filename}...", filename=f"({i+1}/{len(file_paths)})"), end='', flush=True)
            # Skip stdin input if had error
            if os.stat(path).st_ino==os.stat(sys.stdin.fileno()).st_ino and has_error:
                continue
            is_stdin=_globalvar.handle_stdin_prompt(path)
            content_list.append(_globalvar.read_file(path))
            if is_stdin: print() # Print an extra newline
        except Exception as exc:
            print(line_prefix+ \
                fi.feof("read-file-error", "[File {index}] An error occurred while reading the file: \n{message}", \
                    index=str(i+1), message=fmt(path+": "+str(sys.exc_info()[1]))))
            _globalvar.handle_exception()
            has_error=True
    print(line_prefix, end='')
    if has_error: raise direct_exit(1)
    else: return content_list

def main(cli_args: List[str]):
    """
    Use this function invoke 'clitheme' with command line arguments
    
    Note: the first item in the argument list must be a program name (e.g. ['clitheme', <arguments>])
    """
    f=frontend.FetchDescriptor()
    if len(cli_args)<=1: # no arguments passed
        _handle_help_message()
        _handle_usage_error(f.reof("no-command", "Error: no command or option specified"), arg_first)
        return 1

    def check_enough_args(count: int, exclude_options: bool=True):
        c=0
        for arg in cli_args:
            if not exclude_options or not _is_option(arg): c+=1
        if c<count:
            raise direct_exit(_handle_usage_error(f.reof("not-enough-arguments", "Error: not enough arguments"), arg_first))
    def check_extra_args(count: int):
        if len(cli_args)>count:
            raise direct_exit(_handle_usage_error(f.reof("too-many-arguments", "Error: too many arguments"), arg_first))
    try:
        # Don't raise KeyboardInterrupt
        signal.signal(signal.SIGINT if os.name=='posix' else signal.SIGBREAK, signal.SIG_DFL)
    except: pass
    try:
        if cli_args[1] in ("apply-theme", "generate-data", "generate-data-hierarchy"):
            check_enough_args(3)
            generate_only=(cli_args[1] in ("generate-data", "generate-data-hierarchy"))
            paths=[]
            overlay=False
            preserve_temp=False
            no_confirm=False
            for arg in cli_args[2:]:
                if _is_option(arg):
                    if arg.strip()=="--overlay": overlay=True
                    elif arg.strip()=="--preserve-temp" and not generate_only: preserve_temp=True
                    elif arg.strip()=="--yes" and not generate_only: no_confirm=True
                    else: return _handle_usage_error(f.feof("unknown-option", "Error: unknown option \"{option}\"", option=fmt(arg)), arg_first)
                else:
                    paths.append(arg)
            return apply_theme(file_contents=None, overlay=overlay, filenames=paths, preserve_temp=preserve_temp, generate_only=generate_only, no_confirm=no_confirm)
        elif cli_args[1]=="update-theme":
            no_confirm=False
            preserve_temp=False
            for arg in cli_args[2:]:
                if arg.strip()=="--yes": no_confirm=True
                elif arg.strip()=="--preserve-temp": preserve_temp=True
                else: return _handle_usage_error(f.feof("unknown-option", "Error: unknown option \"{option}\"", option=fmt(arg)), arg_first)
            return update_theme(no_confirm=no_confirm, preserve_temp=preserve_temp)
        elif cli_args[1] in ("show-info", "get-current-theme-info"):
            name=False; file_path=False
            for arg in cli_args[2:]:
                if arg.strip()=="--name": name=True
                elif arg.strip()=="--file-path": file_path=True
                else: return _handle_usage_error(f.feof("unknown-option", "Error: unknown option \"{option}\"", option=fmt(arg)), arg_first)
            return show_info(name=name, file_path=file_path)
        elif cli_args[1] in ("remove-theme", "unset-current-theme"):
            no_confirm=False
            for arg in cli_args[2:]:
                if arg.strip()=="--yes": no_confirm=True
                else: return _handle_usage_error(f.feof("unknown-option", "Error: unknown option \"{option}\"", option=fmt(arg)), arg_first)
            return remove_theme(no_confirm=no_confirm)
        elif cli_args[1]=="repair-theme":
            check_extra_args(2)
            return repair_theme()
        elif cli_args[1]=="--version":
            check_extra_args(2)
            print(f.feof("version-str", "CLItheme version {ver}", ver=_globalvar.clitheme_version))
        else:
            if cli_args[1]=="--help":
                check_extra_args(2)
                _handle_help_message(full_help=True)
            else:
                return _handle_usage_error(f.feof("unknown-command", "Error: unknown command \"{cmd}\"", cmd=fmt(cli_args[1])), arg_first)
    except direct_exit as exc: return exc.code
    return 0
def _script_main(): # for script
    return main(sys.argv)
if __name__=="__main__":
    exit(main(sys.argv))
