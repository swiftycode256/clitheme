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
data_path=_globalvar.clitheme_root_data_path+"/theme-data"
global_lang="" # Override locale
class FetchDescriptor():
    """
    Object containing domain and app information used for fetching entries
    """
    def __init__(self, domain_name="", app_name="", debug_mode=False, disable_lang=False):
        """
        Create a new instance of the object.
        
        - Provide domain_name and app_name to automatically append them for retrival functions.
        - Set debug_mode=True to output underlying operations when retriving entries.
        - Set disable_lang=True to disable localization detection and use "default" entry for all retrival operations
        """
        # Leave domain and app names blank for global reference
        self.domain_name=domain_name
        self.app_name=app_name
        self.debug_mode=debug_mode
        self.disable_lang=disable_lang
    def retrive_entry_or_fallback(self, entry_path, fallback_string):
        """
        Attempt to retrieve the entry based on given entry path. 
        If the entry does not exist, use the provided fallback string instead.
        """
        # entry_path e.g. "class-a sample_text"

        # Prevent leading . & prevent /,\ in entry name
        for p in entry_path.split():
            if p.startswith('.'):
                if self.debug_mode: 
                    print("Error: entry subsections/names cannot start with '.'")
                    return fallback_string
            for b in _globalvar.entry_banphrases:
                if p.find(b)!=-1:
                    if self.debug_mode: 
                        print("Error: entry subsections/names cannot contain '{}'".format(b))
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
        path=data_path+"/"+self.domain_name+"/"+self.app_name
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
    def entry_exists(self, entry_path):
        """
        Check if the entry at the given entry path exists.

        Returns true if exists and false if does not exist
        """
        # just being lazy here I don't want to rewrite this all over this again ಥ_ಥ
        fallback_string=""
        for x in range(30): 
            fallback_string+=random.choice(string.ascii_letters)
        recieved_content=self.retrive_entry_or_fallback(entry_path, fallback_string)
        if recieved_content.strip()==fallback_string:
            return False
        else: return True