"""
CLItheme fallback frontend for version 2.0 (returns fallback values for all functions)
"""
from typing import Optional, List

data_path=""

global_domain=""
global_appname=""
global_subsections=""
global_debugmode=False
global_lang=""
global_disablelang=False

def set_domain(value: Optional[str]): pass
def set_appname(value: Optional[str]): pass
def set_subsections(value: Optional[str]): pass
def set_debugmode(value: Optional[bool]): pass
def set_lang(value: Optional[str]): pass
def set_disablelang(value: Optional[bool]): pass

alt_path=None
alt_path_dirname=None
alt_path_hash=None

def set_local_themedef(file_content: str, overlay: bool=False) -> bool:
    """Fallback set_local_themedef function (always returns False)"""
    return False
def set_local_themedefs(file_contents: List[str], overlay: bool=False):
    """Fallback set_local_themedefs function (always returns False)"""
    return False
def unset_local_themedef():
    """Fallback unset_local_themedef function"""
    return

class FetchDescriptor():
    """
    Object containing domain and app information used for fetching entries
    """
    def __init__(self, domain_name: Optional[str] = None, app_name: Optional[str] = None, subsections: Optional[str] = None, lang: Optional[str] = None, debug_mode: Optional[bool] = None, disable_lang: Optional[bool] = None):
        """Fallback init function"""
        return
    def retrieve_entry_or_Fallback(self, entry_path: str, fallback_string: str) -> str:
        """Fallback retrieve_entry_or_Fallback function (always return Fallback string)"""
        return fallback_string
    reof=retrieve_entry_or_Fallback # a shorter alias of the function
    def format_entry_or_fallback(self, entry_path: str, fallback_string: str, *args, **kwargs) -> str:
        return fallback_string.format(*args, **kwargs)
    feof=format_entry_or_fallback
    def entry_exists(self, entry_path: str) -> bool:
        """Fallback entry_exists function (always return false)"""
        return False