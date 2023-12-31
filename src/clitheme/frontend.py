"""
clitheme front-end interface for accessing entries
"""

import os,sys
import random
import string
import re
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
                lang=self.lang
            else:
                if self.debug_mode: print("[Debug] Locale: Using environment variables")
                # $LANGUAGE (list of languages separated by colons)
                if os.environ.__contains__("LANGUAGE"):
                    target_str=os.environ['LANGUAGE']
                    for each_language in target_str.strip().split(":"):
                        # avoid exploit of accessing top-level folders
                        if each_language.startswith("."): continue
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
                    if not target_str.startswith("."): 
                        lang=target_str+" "
                        lang+=re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str)
                # $LANG
                elif os.environ.__contains__("LANG"):
                    target_str=os.environ["LANG"].strip()
                    if not target_str.startswith("."): 
                        lang=target_str+" "
                        lang+=re.sub(r"(?P<locale>.+)[\.].+", r"\g<locale>", target_str)

        if self.debug_mode: print(f"[Debug] lang: {lang}\n[Debug] entry_path: {entry_path}")
        # just being lazy here I don't want to check the variables before using ಥ_ಥ (because it doesn't matter) 
        path=data_path+"/"+self.domain_name+"/"+self.app_name+"/"+self.subsections
        for section in entry_path.split():
            path+="/"+section
        # path with lang, path with lang but without e.g. .UTF-8, path with no lang
        possible_paths=[]
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

    def entry_exists(self, entry_path: str) -> bool:
        """
        Check if the entry at the given entry path exists.
        Returns true if exists and false if does not exist
        """
        # just being lazy here I don't want to rewrite this all over again ಥ_ಥ
        fallback_string=""
        for x in range(30): 
            fallback_string+=random.choice(string.ascii_letters)
        recieved_content=self.retrieve_entry_or_fallback(entry_path, fallback_string)
        if recieved_content.strip()==fallback_string: return False
        else: return True
