"""
clitheme front-end interface for accessing entries
"""

import os,sys
import random
import string
import re
import hashlib
from typing import Optional
try:
    from . import _globalvar
except ImportError: # for test program
    import _globalvar
data_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_data_pathname

global_domain=""
global_appname=""
global_subsections=""
global_debugmode=False
global_lang="" # Override locale
global_disablelang=False

alt_path=None
alt_path_dirname=None
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
    global alt_path_dirname
    dir_name=f"clitheme-data-{h.hexdigest(6)}" # length of 12 (6*2)
    if alt_path_dirname!=None and overlay==True: # overlay
        dir_name=alt_path_dirname
    path_name=_globalvar.clitheme_temp_root+"/"+dir_name
    if global_debugmode: print("[Debug] "+path_name)
    # Generate data hierarchy as needed
    if not os.path.exists(path_name):
        _generator.path=path_name
        try:
            _generator.generate_data_hierarchy(file_content, custom_path_gen=False)
        except SyntaxError:
            if global_debugmode: print("[Debug] Generator error: "+str(sys.exc_info()[1]))
            return False
    global alt_path
    alt_path=path_name+"/"+_globalvar.generator_data_pathname
    alt_path_dirname=dir_name
    return True
def unset_local_themedef():
    """
    Unsets the local theme definition file for the current frontend instance.
    After this operation, FetchDescriptor functions will no longer use local definitions.
    """
    global alt_path; alt_path=None
    global alt_path_dirname; alt_path_dirname=None

class FetchDescriptor():
    """
    Object containing domain and app information used for fetching entries
    """
    def __init__(self, domain_name: Optional[str] = None, app_name: Optional[str] = None, subsections: Optional[str] = None, lang: Optional[str] = None, debug_mode: Optional[bool] = None, disable_lang: Optional[bool] = None):
        """
        Create a new instance of the object.
        
        - Provide domain_name and app_name to automatically append them for retrieval functions.
        - Provide subsections to automatically append them after domain_name+app_name
        - Provide lang to override the automatically detected system locale information
        - Set debug_mode=True to output underlying operations when retrieving entries.
        - Set disable_lang=True to disable localization detection and use "default" entry for all retrieval operations
        """
        # Leave domain and app names blank for global reference

        if domain_name==None:
            self.domain_name=global_domain.strip()
        else:
            self.domain_name=domain_name.strip()

        if app_name==None:
            self.app_name=global_appname.strip()
        else:
            self.app_name=app_name.strip()

        if subsections==None:
            self.subsections=global_subsections.strip()
        else:
            self.subsections=subsections.strip()

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
        if _globalvar.sanity_check(self.domain_name+" "+self.app_name+" "+self.subsections)==False:
            raise SyntaxError("Domain, app, or subsection names {}".format(_globalvar.sanity_check_error_message))
    def retrieve_entry_or_fallback(self, entry_path: str, fallback_string: str) -> str:
        """
        Attempt to retrieve the entry based on given entry path. 
        If the entry does not exist, use the provided fallback string instead.
        """
        # entry_path e.g. "class-a sample_text"

        # Sanity check the path
        if _globalvar.sanity_check(entry_path)==False:
            if self.debug_mode: print("Error: entry names/subsections {}".format(_globalvar.sanity_check_error_message))
            return fallback_string
        lang=""
        # Language handling: see https://www.gnu.org/software/gettext/manual/gettext.html#Locale-Environment-Variables for more information
        if not self.disable_lang:
            if self.lang!="":
                if self.debug_mode: print("[Debug] Locale: Using defined self.lang")
                if not _globalvar.sanity_check(self.lang)==False:
                    lang=self.lang
                else:
                    if self.debug_mode: print("[Debug] Locale: sanity check failed")
            else:
                if self.debug_mode: print("[Debug] Locale: Using environment variables")
                # $LANGUAGE (list of languages separated by colons)
                if os.environ.__contains__("LANGUAGE"):
                    target_str=os.environ['LANGUAGE']
                    for each_language in target_str.strip().split(":"):
                        # avoid exploit of accessing top-level folders
                        if _globalvar.sanity_check(each_language)==False: continue
                        # Ignore en and en_US (See https://wiki.archlinux.org/title/Locale#LANGUAGE:_fallback_locales)
                        if each_language!="en" and each_language!="en_US":
                            # Treat C as en_US also
                            if re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", each_language)=="C":
                                lang+=re.sub(r".+[\.]", "en_US.", each_language)+" "
                                lang+="en_US"+" "
                            lang+=each_language+" "
                            # no encoding
                            lang+=re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", each_language)+" "
                    lang=lang.strip()
                # $LC_ALL
                elif os.environ.__contains__("LC_ALL"):
                    target_str=os.environ["LC_ALL"].strip()
                    if not _globalvar.sanity_check(target_str)==False:
                        lang=target_str+" "
                        lang+=re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str)
                    else:
                        if self.debug_mode: print("[Debug] Locale: sanity check failed")
                # $LANG
                elif os.environ.__contains__("LANG"):
                    target_str=os.environ["LANG"].strip()
                    if not _globalvar.sanity_check(target_str)==False:
                        lang=target_str+" "
                        lang+=re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str)
                    else:
                        if self.debug_mode: print("[Debug] Locale: sanity check failed")

        if self.debug_mode: print(f"[Debug] lang: {lang}\n[Debug] entry_path: {entry_path}")
        # just being lazy here I don't want to check the variables before using ಥ_ಥ (because it doesn't matter) 
        path=data_path+"/"+self.domain_name+"/"+self.app_name+"/"+self.subsections
        path2=None
        if alt_path!=None: path2=alt_path+"/"+self.domain_name+"/"+self.app_name+"/"+self.subsections
        for section in entry_path.split():
            path+="/"+section
            if path2!=None: path2+="/"+section
        # path with lang, path with lang but without e.g. .UTF-8, path with no lang
        possible_paths=[]
        if path2!=None:
            for l in lang.split():
                possible_paths.append(path2+"__"+l)
            possible_paths.append(path2)
        for l in lang.split():
            possible_paths.append(path+"__"+l)
        possible_paths.append(path)
        for p in possible_paths:
            if self.debug_mode: print("Trying "+p, end="...")
            try:
                f=open(p,'r', encoding="utf-8")
                dat=f.read()
                if self.debug_mode: print("Success:\n> "+dat)
                # since the generator adds an extra newline in the entry data, we need to remove it
                return re.sub(r"\n\Z", "", dat)
            except (FileNotFoundError, IsADirectoryError):
                if self.debug_mode: print("Failed")
        return fallback_string
    
    reof=retrieve_entry_or_fallback # a shorter alias of the function

    def format_entry_or_fallback(self, entry_path: str, fallback_string: str, *args, **kwargs) -> str:
        """
        Attempt to retrieve and format the entry based on given entry path and arguments. 
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
        recieved_content=self.retrieve_entry_or_fallback(entry_path, fallback_string)
        if recieved_content.strip()==fallback_string: return False
        else: return True
