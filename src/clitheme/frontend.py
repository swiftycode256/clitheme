# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
clitheme frontend interface for accessing entries

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
from typing import Optional
from . import _globalvar

# spell-checker:ignore newhash numorig numcur

data_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_data_pathname

global_domain=""
global_appname=""
global_subsections=""
global_debugmode=False
global_lang="" # Override locale
global_disablelang=False

_alt_path=None
_alt_path_dirname=None
_alt_path_hash=None
# Support for setting a local definition file
# - Generate the data in a temporary directory named after content hash
# - First try alt_path then data_path

def set_local_themedef(file_content: str, overlay: bool=False) -> bool:
    """
    Sets a local theme definition file for the current frontend instance.
    When set, the FetchDescriptor functions will try the local definition before falling back to global theme data.

    - Set overlay=True to overlay on top of existing local definition data (if exists)
    
    WARNING: Pass the file content in str to this function; DO NOT pass the path to the file.
    
    This function returns True if successful, otherwise returns False.
    """
    try: from . import _generator
    except ImportError: import _generator
    # Determine directory name
    h=hashlib.shake_256(bytes(file_content, "utf-8"))
    d=h.hexdigest(6) # length of 12 (6*2)
    global _alt_path_hash
    local_path_hash=_alt_path_hash
    # if overlay, update hash with new contents of file
    if _alt_path_hash!=None and overlay==True:
        newhash=""
        for x in range(len(_alt_path_hash)):
            chart=string.ascii_uppercase+string.ascii_lowercase+string.digits
            numorig=0
            numcur=0
            if d[x]>='A' and d[x]<='Z': #uppercase letters
                numorig=ord(d[x])-ord('A')
            elif d[x]>='a' and d[x]<='z': #lowercase letters
                numorig=(ord(d[x])-ord('a'))+len(string.ascii_uppercase)
            elif d[x]>='0' and d[x]<='9': #digit
                numorig=ord(d[x])-ord('0')+len(string.ascii_uppercase+string.ascii_lowercase)
            if _alt_path_hash[x]>='A' and _alt_path_hash[x]<='Z': #uppercase letters
                numcur=ord(_alt_path_hash[x])-ord('A')
            elif _alt_path_hash[x]>='a' and _alt_path_hash[x]<='z': #lowercase letters
                numcur=(ord(_alt_path_hash[x])-ord('a'))+len(string.ascii_uppercase)
            elif _alt_path_hash[x]>='0' and _alt_path_hash[x]<='9': #digit
                numcur=ord(_alt_path_hash[x])-ord('0')+len(string.ascii_uppercase+string.ascii_lowercase)
            newhash+=chart[(numorig+numcur)%len(chart)]
        local_path_hash=newhash
    else: local_path_hash=d # else, use generated hash
    dir_name=f"clitheme-data-{local_path_hash}"
    _generator.generate_custom_path() # prepare _generator.path
    global _alt_path_dirname
    path_name=_globalvar.clitheme_temp_root+"/"+dir_name
    if _alt_path_dirname!=None and overlay==True: # overlay
        shutil.copytree(_globalvar.clitheme_temp_root+"/"+_alt_path_dirname, _generator.path)
    if global_debugmode: print("[Debug] "+path_name)
    # Generate data hierarchy as needed
    if not os.path.exists(path_name):
        _generator.silence_warn=True
        return_val: str
        try:
            return_val=_generator.generate_data_hierarchy(file_content, custom_path_gen=False)
        except SyntaxError:
            if global_debugmode: print("[Debug] Generator error: "+str(sys.exc_info()[1]))
            return False
        # I GIVE UP on solving the callback cycle HELL on _generator.generate_data_hierarchy -> new GeneratorObject -> db_interface import -> set_local_themedef -> [generates data directory] so I'm going to add this CRAP fix
        if not os.path.exists(path_name):
            shutil.copytree(return_val, path_name)
        try: shutil.rmtree(return_val)
        except: pass
    global _alt_path
    _alt_path_hash=local_path_hash
    _alt_path=path_name+"/"+_globalvar.generator_data_pathname
    _alt_path_dirname=dir_name
    return True
def unset_local_themedef():
    """
    Unsets the local theme definition file for the current frontend instance.
    After this operation, FetchDescriptor functions will no longer use local definitions.
    """
    global _alt_path; _alt_path=None
    global _alt_path_dirname; _alt_path_dirname=None
    global _alt_path_hash; _alt_path_hash=None

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

        if domain_name==None:
            self.domain_name=global_domain.strip()
        else:
            self.domain_name=domain_name.strip()
        if len(self.domain_name.split())>1:
            raise SyntaxError("Only one phrase is allowed for domain_name")

        if app_name==None:
            self.app_name=global_appname.strip()
        else:
            self.app_name=app_name.strip()
        if len(self.app_name.split())>1:
            raise SyntaxError("Only one phrase is allowed for app_name")

        if subsections==None:
            self.subsections=global_subsections.strip()
        else:
            self.subsections=subsections.strip()
        self.subsections=re.sub(" {2,}", " ", self.subsections)

        if lang==None:
            self.lang=global_lang.strip()
        else:
            self.lang=lang.strip()
        
        if debug_mode==None:
            self.debug_mode=global_debugmode
        else:
            self.debug_mode=debug_mode

        if disable_lang==None:
            self.disable_lang=global_disablelang
        else:
            self.disable_lang=disable_lang

        # sanity check the domain, app, and subsections
        if _globalvar.sanity_check(self.domain_name+" "+self.app_name+" "+self.subsections, use_orig=True)==False:
            raise SyntaxError("Domain, app, or subsection names {}".format(_globalvar.sanity_check_error_message))
    def retrieve_entry_or_fallback(self, entry_path: str, fallback_string: str) -> str:
        """
        Attempt to retrieve the entry based on given entry path. 
        If the entry does not exist, use the provided fallback string instead.
        """
        # entry_path e.g. "class-a sample_text"

        # Sanity check the path
        if entry_path.strip()=="":
            raise SyntaxError("Empty entry name")
        if _globalvar.sanity_check(entry_path, use_orig=True)==False:
            raise SyntaxError("Entry names and subsections {}".format(_globalvar.sanity_check_error_message))
        lang=[]
        # Language handling: see https://www.gnu.org/software/gettext/manual/gettext.html#Locale-Environment-Variables for more information
        if not self.disable_lang:
            if self.lang!="":
                if self.debug_mode: print("[Debug] Locale: Using defined self.lang")
                if not _globalvar.sanity_check(self.lang, use_orig=True)==False:
                    lang=[self.lang]
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
                dat=re.sub(r"\n\Z", "", f.read())
                if self.debug_mode: print("Success:\n> "+dat)
                # since the generator adds an extra newline in the entry data, we need to remove it
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
