"""
clitheme front-end interface for accessing entries
"""

import os,sys
import random
import string
try:
    from . import _globalvar
except ImportError: # for test program
    import _globalvar
data_path=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_data_pathname
global_lang="" # Override locale
class FetchDescriptor():
    """
    Object containing domain and app information used for fetching entries
    """
    def __init__(self, domain_name: str = "", app_name: str = "", subsections: str = "", debug_mode: bool = False, disable_lang: bool = False):
        """
        Create a new instance of the object.
        
        - Provide domain_name and app_name to automatically append them for retrieval functions.
        - Provide subsections to automatically append them after domain_name+app_name
        - Set debug_mode=True to output underlying operations when retrieving entries.
        - Set disable_lang=True to disable localization detection and use "default" entry for all retrieval operations
        """
        # Leave domain and app names blank for global reference

        # sanity check the domain, app, and subsections
        if _globalvar.sanity_check(domain_name+" "+app_name+" "+subsections)==False:
            raise SyntaxError("Domain, app, or subsection names {}".format(_globalvar.sanity_check_error_message))

        self.domain_name=domain_name.strip()
        self.app_name=app_name.strip()
        self.subsections=subsections.strip()
        self.debug_mode=debug_mode
        self.disable_lang=disable_lang
    def retrieve_entry_or_fallback(self, entry_path: str, fallback_string: str):
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
        lang_without_encoding=""
        if not self.disable_lang:
            if global_lang!="":
                lang=global_lang
            elif os.environ.__contains__("LANG"):
                lang=os.environ["LANG"]
            if lang.strip()!="": # not empty
                for char in lang:
                    if char=='.': # if reaches e.g. ".UTF-8" section
                        break
                    lang_without_encoding+=char 
        if self.debug_mode: print("[Debug]", lang, lang_without_encoding, entry_path)
        path=data_path+"/"+self.domain_name+"/"+self.app_name+"/"+self.subsections
        for section in entry_path.split():
            path+="/"+section
        # path with lang, path with lang but without e.g. .UTF-8, path wth no lang
        possible_paths=[path+"__"+lang, path+"__"+lang_without_encoding, path]
        for p in possible_paths:
            if self.debug_mode: print("Trying "+p, end="...")
            try:
                f=open(p,'r')
                dat=f.read().strip()
                if self.debug_mode: print("Success:\n> "+dat)
                return dat
            except (FileNotFoundError, IsADirectoryError):
                if self.debug_mode: print("Failed")
        return fallback_string
    def entry_exists(self, entry_path: str):
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