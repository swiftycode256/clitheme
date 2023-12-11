"""
clitheme fallback frontend for 1.0 (returns fallback values for all functions)
"""
import os,sys
import random
import string
from typing import Optional

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
        """fallback init function"""
        return
    def retrieve_entry_or_fallback(self, entry_path: str, fallback_string: str) -> str:
        """fallback retrieve_entry_or_fallback function (always return fallback string)"""
        return fallback_string
    reof=retrieve_entry_or_fallback # a shorter alias of the function
    def entry_exists(self, entry_path: str) -> bool:
        """fallback entry_exists function (always return false)"""
        return False