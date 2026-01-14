# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
CLItheme frontend interface for accessing entries

- Create a FetchDescriptor instance and optionally pass information such as domain&app name and subsections
- Use the 'retrieve_entry_or_fallback' or 'reof' function in the instance to retrieve content of an entry definition
- Use the 'format_entry_or_fallback' or 'feof' function in the instance to retrieve and format content of entry definition using str.format
"""

import os,sys
import random
import string
import re
import hashlib
import shutil
import inspect
from typing import Optional, List, Union, Dict
from . import _globalvar

data_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_data_pathname

_setting_defs: Dict[str, type]={
    "domain": str,
    "appname": str,
    "subsections": str,
    "debugmode": bool,
    "lang": str,
    "disablelang": bool,
}

_local_settings: Dict[str, Dict[str, Union[None,str,bool]]]={}

for name in _setting_defs.keys():
    _local_settings[name]={}

def _get_caller(outer_level=3) -> str:
    stack=inspect.stack()
    assert len(stack)>=outer_level+1, "Cannot determine filename from call stack"
    # inspect.stack(): [0: this function, 1: update/get settings, 2: function in frontend module, 3: target calling function]
    filename=stack[outer_level].filename
    # Find the first function in the stack OUTSIDE of frontend module
    # (The stack[3] may also be some function in frontend)
    for x in range(outer_level,len(stack)):
        filename=stack[x].filename
        if filename!=__file__: break
    return filename

def _update_local_settings(key: str, value: Union[None,str,bool]):
    caller=_get_caller()
    _local_settings[key][caller]=value
    if _get_setting("debugmode", caller)==True:
        print(f"[Debug] Set {key}={value} for file \"{caller}\"")
        

_desc=\
"""
Set default value for `{}` option in future FetchDescriptor instances.
This setting is valid for the module/code file that invokes this function.

- Set value=None to unset the default value and use values defined in global variables
- Change global variables (e.g. global_domain, global_debugmode) to set the default value for all files in an invoking module
"""

def set_domain(value: Optional[str]): _update_local_settings("domain", value)
def set_appname(value: Optional[str]): _update_local_settings("appname", value)
def set_subsections(value: Optional[str]): _update_local_settings("subsections", value)
def set_debugmode(value: Optional[bool]): _update_local_settings("debugmode", value)
def set_lang(value: Optional[str]): _update_local_settings("lang", value)
def set_disablelang(value: Optional[bool]): _update_local_settings("disablelang", value)

global_domain=""
global_appname=""
global_subsections=""
global_debugmode=False
global_lang="" # Override locale
global_disablelang=False

def _get_setting(key: str, caller: Optional[str]=None) -> Union[str,bool]:
    # Get local settings
    value=_local_settings[key].get(caller if caller!=None else _get_caller())
    if value!=None: return value
    # Get global settings if not found
    else:
        return eval(f"global_{key}")

_alt_path: Optional[str]=None
_alt_path_dirname: Optional[str]=None
_alt_path_hash: Optional[bytes]=None
_alt_info_index: int=1 # Next info index

# Support for setting a local definition file
# - Generate the data in a temporary directory named after content hash
# - First try alt_path then data_path

def _generate_data(file_contents: List[str], path_name: str, overlay: bool) -> bool:
    """
    Handle generate data operation for set_local_themedef[s] functions
    """
    global global_debugmode, _alt_info_index
    if _get_setting("debugmode"): print("[Debug] set_local_themedef data path: "+path_name)
    # Generate data hierarchy as needed
    if not os.path.exists(path_name):
        from . import _generator
        _generator.generate_custom_path() # prepare _generator.path
        if overlay==True and _alt_path_dirname!=None:
            shutil.copytree(_globalvar.clitheme_temp_root+"/"+_alt_path_dirname, _generator.path)
        else: _alt_info_index=1
        d_copy=global_debugmode
        for x in range(len(file_contents)):
            file_content=file_contents[x]
            if _get_setting("debugmode") and len(file_contents)>1:
                print(f"[Debug] set_local_themedefs: Processing file {x+1} of {len(file_contents)}")
            try:
                global_debugmode=False
                return_val=_generator.generate_data_hierarchy(file_content, custom_path_gen=False, custom_infofile_name=str(_alt_info_index))
                assert return_val.success, '\n'.join(return_val.messages)
                _alt_info_index+=1
            except AssertionError:
                if _get_setting("debugmode"): print("[Debug] Generator error: "+str(sys.exc_info()[1]))
                return False
            finally: global_debugmode=d_copy
        if not os.path.exists(path_name):
            shutil.copytree(return_val.dir_path, path_name)
        try: shutil.rmtree(return_val.dir_path)
        except: pass
    else:
        if _get_setting("debugmode"): print("[Debug] NOTE: Data path already exists, not generating data")
    return True
def _get_dir_name(hash: bytes, index: int) -> str:
    h=hashlib.shake_256(hash)
    local_path_hash="O"+str(index)+h.hexdigest(5)
    dir_name=f"clitheme-data-{local_path_hash}"
    return dir_name

def set_local_themedef(file_content: str, overlay: bool=False) -> bool:
    """
    Sets a local theme definition file for the current frontend instance.
    When set, the FetchDescriptor functions will fall back to the local definition after trying global theme data.

    - Set overlay=True to overlay on top of existing local definition data (if exists)
    
    WARNING: Pass the file content in str to this function; DO NOT pass the path to the file.
    
    This function returns True if successful, otherwise returns False.
    """
    global _alt_path, _alt_path_hash, _alt_path_dirname, _alt_info_index
    h=hashlib.sha1(bytes(file_content, "utf-8")).digest()
    # File hash generation
    # if overlay, update hash with new contents of file
    new_path_hash=_alt_path_hash
    if new_path_hash!=None and overlay==True:
        new_path_hash+=h # append
    else: new_path_hash=h # override
    dir_name=_get_dir_name(new_path_hash, _alt_info_index if overlay else 1)
    path_name=_globalvar.clitheme_temp_root+"/"+dir_name

    if not _generate_data([file_content], path_name, overlay): return False

    # Update everything after success
    _alt_path_hash=new_path_hash
    _alt_path=path_name+"/"+_globalvar.generator_data_pathname
    _alt_path_dirname=dir_name
    return True

def set_local_themedefs(file_contents: List[str], overlay: bool=False):
    """
    Sets multiple local theme definition files for the current frontend instance.
    When set, the FetchDescriptor functions will fall back to the local definition after trying global theme data.

    - Set overlay=True to overlay on top of existing local definition data (if exists)
    
    WARNING: Pass the file content in str to this function; DO NOT pass the path to the file.
    
    This function returns True if successful, otherwise returns False.
    """
    if len(file_contents)==0:
        raise ValueError("Empty file_contents array")
    global _alt_path, _alt_path_hash, _alt_path_dirname, _alt_info_index
    # File hash generation
    # if overlay, update hash with new contents of file
    path_hash: bytes=_alt_path_hash if overlay and _alt_path_hash!=None else b""
    for file_content in file_contents:
        path_hash+=hashlib.sha1(bytes(file_content, 'utf-8')).digest()
    dir_name=_get_dir_name(path_hash, (_alt_info_index if overlay else 1)+len(file_contents)-1)
    path_name=_globalvar.clitheme_temp_root+"/"+dir_name

    if not _generate_data(file_contents, path_name, overlay): return False

    # Update everything after success
    _alt_path_hash=path_hash
    _alt_path=path_name+"/"+_globalvar.generator_data_pathname
    _alt_path_dirname=dir_name
    return True

def unset_local_themedef():
    """
    Unset the local theme definition file for the current frontend instance.
    After this operation, FetchDescriptor functions will no longer use local definitions.
    """
    global _alt_path; _alt_path=None
    global _alt_path_dirname; _alt_path_dirname=None
    global _alt_path_hash; _alt_path_hash=None
    global _alt_info_index; _alt_info_index=1

class FetchDescriptor():
    """
    Object containing domain and app information used for fetching entries
    """
    def __init__(self, domain_name: Optional[str] = None, app_name: Optional[str] = None, subsections: Optional[str] = None, lang: Optional[str] = None, debug_mode: Optional[bool] = None, disable_lang: Optional[bool] = None):
        """
        Create a new instance of the object.
        
        - Provide domain_name and app_name to automatically append them for retrieval functions
        - Provide subsections to automatically append them after domain_name+app_name
        - Provide lang to override the automatically detected system locale information
        - Set debug_mode=True to output underlying operations when retrieving entries (debug purposes only)
        - Set disable_lang=True to disable localization detection and use "default" entry for all retrieval operations
        """
        # Leave domain and app names blank for global reference

        # stack: [0: get caller, 1: this function, 2: outer function]
        caller=_get_caller(outer_level=2)
        if domain_name==None:
            self.domain_name: str=_get_setting("domain", caller).strip() #type:ignore
        else:
            self.domain_name=domain_name.strip()
        if len(self.domain_name.split())>1:
            raise ValueError("Only one phrase is allowed for domain_name")

        if app_name==None:
            self.app_name: str=_get_setting("appname", caller).strip() #type:ignore
        else:
            self.app_name=app_name.strip()
        if len(self.app_name.split())>1:
            raise ValueError("Only one phrase is allowed for app_name")

        if subsections==None:
            self.subsections: str=_get_setting("subsections", caller).strip() #type:ignore
        else:
            self.subsections=subsections.strip()
        self.subsections=re.sub(" {2,}", " ", self.subsections)

        if lang==None:
            self.lang=_get_setting("lang", caller).strip() #type:ignore
        else:
            self.lang=lang.strip()
        
        if debug_mode==None:
            self.debug_mode: bool=_get_setting("debugmode", caller) #type:ignore
        else:
            self.debug_mode=debug_mode

        if disable_lang==None:
            self.disable_lang: bool=_get_setting("disablelang", caller) #type:ignore
        else:
            self.disable_lang=disable_lang

        # sanity check the domain, app, and subsections
        if _globalvar.sanity_check(self.domain_name+"_"+self.app_name+"_"+self.subsections, use_orig=True)==False:
            raise ValueError("Domain, app, or subsection names {}".format(_globalvar.sanity_check_error_message))
    def retrieve_entry_or_fallback(self, entry_path: str, fallback_string: str) -> str:
        """
        Attempt to retrieve the entry based on given entry path. 
        If the entry does not exist, use the provided fallback string instead.
        """
        # entry_path e.g. "class-a sample_text"

        # Sanity check the path
        if entry_path.strip()=="":
            raise ValueError("Empty entry name")
        if _globalvar.sanity_check(entry_path, use_orig=True)==False:
            raise ValueError("Entry names and subsections {}".format(_globalvar.sanity_check_error_message))
        lang=[]
        # Language handling: see https://www.gnu.org/software/gettext/manual/gettext.html#Locale-Environment-Variables for more information
        if not self.disable_lang:
            if self.lang!="":
                if self.debug_mode: print("[Debug] Locale: Using defined self.lang")
                if not _globalvar.sanity_check(self.lang, use_orig=True)==False:
                    lang=[self.lang]
                    if re.match(r"^(?P<locale>.+)[\.].+$", self.lang)!=None:
                        # e.g. en_US.UTF-8 -> en_US
                        no_encoding=re.sub(r"^(?P<locale>.+)[\.].+$", r"\g<locale>", self.lang)
                        lang.append(no_encoding)
                else:
                    if self.debug_mode: print("[Debug] Locale: sanity check failed ({})".format(_globalvar.sanity_check_error_message))
            else:
                if self.debug_mode: print("[Debug] Locale: Using environment variables")
                lang=_globalvar.get_locale(debug_mode=self.debug_mode)

        if self.debug_mode: print(f"[Debug] lang: {lang}\n[Debug] entry_path: {entry_path}")
        # just being lazy here I don't want to check the variables before using ಥ_ಥ (because it doesn't matter) 
        path=data_path+"/"+self.domain_name+"/"+self.app_name+"/"+re.sub(" ",r"/", self.subsections)
        path2=None
        if _alt_path!=None: path2=_alt_path+"/"+self.domain_name+"/"+self.app_name+"/"+re.sub(" ",r"/", self.subsections)
        for section in entry_path.split():
            path+="/"+section
            if path2!=None: path2+="/"+section
        # path with lang, path with lang but without e.g. .UTF-8, path with no lang
        possible_paths=[]
        for l in lang:
            possible_paths.append(path+"__"+l)
        possible_paths.append(path)
        if path2!=None:
            for l in lang:
                possible_paths.append(path2+"__"+l)
            possible_paths.append(path2)
        for p in possible_paths:
            if self.debug_mode: print("Trying "+p, end=" ...")
            try:
                f=open(p,'r', encoding="utf-8")
                # since the generator adds an extra newline in the entry data, we need to remove it
                dat=re.sub(r"\n\Z", "", f.read())
                if self.debug_mode: print("Success:\n> "+dat)
                return dat
            except (FileNotFoundError, IsADirectoryError):
                if self.debug_mode: print("Failed")
        return fallback_string
    
    reof=retrieve_entry_or_fallback # a shorter alias of the function

    def format_entry_or_fallback(self, entry_path: str, fallback_string: str, *args, **kwargs) -> str:
        """
        Attempt to retrieve and format the entry using str.format based on given entry path and arguments. 
        If the entry does not exist or an error occurs while formatting the entry string, use the provided fallback string instead.
        """
        # retrieve the entry
        if not self.entry_exists(entry_path): 
            if self.debug_mode: print("[Debug] Entry not found")
            return fallback_string.format(*args, **kwargs)
        entry=self.retrieve_entry_or_fallback(entry_path, "")
        # format the string
        try:
            return entry.format(*args, **kwargs)
        except Exception:
            if self.debug_mode: print("[Debug] Format error: {err}".format(err=str(sys.exc_info()[1])))
            return fallback_string.format(*args, **kwargs)
    feof=format_entry_or_fallback # a shorter alias of the function
            
    def entry_exists(self, entry_path: str) -> bool:
        """
        Check if the entry at the given entry path exists.
        Returns true if exists and false if does not exist.
        """
        # just being lazy here I don't want to rewrite this all over again ಥ_ಥ
        fallback_string=""
        for x in range(30): 
            fallback_string+=random.choice(string.ascii_letters)
        received_content=self.retrieve_entry_or_fallback(entry_path, fallback_string)
        if received_content.strip()==fallback_string: return False
        else: return True
