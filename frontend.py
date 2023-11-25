import os,sys
import _globalvar

data_path=_globalvar.clitheme_root_data_path+"/theme-data"
global_lang="" # Override locale
class FetchDescriptor():
    def __init__(self, domain_name="", app_name="", debug_mode=False):
        # Leave domain and app names blank for global reference
        self.domain_name=domain_name
        self.app_name=app_name
        self.debug_mode=debug_mode
    def retrive_entry_or_fallback(self, entry_path, fallback_string):
        # entry_path e.g. "class-a sample_text"
        lang=""
        lang_without_encoding=""
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