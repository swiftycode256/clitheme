# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
entries_section parser function (internal module)
"""
from typing import Optional
from .. import _globalvar
from . import _dataclass

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_entries_section(obj: _dataclass.GeneratorObject, first_phrase: str):
    obj.handle_begin_section("entries")
    # --Process entries/main block--
    end_phrase="end_main" if first_phrase=="begin_main" else r"{/entries_section}"
    if first_phrase=="begin_main":
        obj.handle_warning(obj.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=str(obj.lineindex+1), old_phrase="begin_main", new_phrase=r"{entries_section}"))
    domainapp=""
    subsection=""
    while obj.lineindex<len(obj.lines_data)-1:
        obj.lineindex+=1
        if obj.is_ignore_line(): continue
        phrases=obj.lines_data[obj.lineindex].split()
        if phrases[0]=="in_domainapp":
            this_phrases=obj.subst_variable_content(obj.lines_data[obj.lineindex].strip()).split()
            obj.check_enough_args(this_phrases, 3)
            obj.check_extra_args(this_phrases, 3, use_exact_count=False)
            domainapp=this_phrases[1]+" "+this_phrases[2]
            if _globalvar.sanity_check(domainapp)==False:
                obj.handle_error(obj.fd.feof("sanity-check-domainapp-err", "Line {num}: domain and app names {sanitycheck_msg}", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
            subsection="" # clear subsection
        elif phrases[0]=="in_subsection":
            obj.check_enough_args(phrases, 2)
            subsection=_globalvar.splitarray_to_string(phrases[1:])
            subsection=obj.subst_variable_content(subsection)
            if _globalvar.sanity_check(subsection)==False:
                obj.handle_error(obj.fd.feof("sanity-check-subsection-err", "Line {num}: subsection names {sanitycheck_msg}", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
        elif phrases[0]=="unset_domainapp":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            domainapp=""; subsection=""
        elif phrases[0]=="unset_subsection":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            subsection=""
        elif phrases[0]=="entry" or phrases[0]=="[entry]":
            obj.check_enough_args(phrases, 2)
            entry_name=_globalvar.extract_content(obj.lines_data[obj.lineindex])
            entry_name=obj.subst_variable_content(entry_name)
            # Prevent leading . & prevent /,\ in entry name
            if _globalvar.sanity_check(entry_name)==False:
                obj.handle_error(obj.fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
            if subsection!="": entry_name=subsection+" "+entry_name
            if domainapp!="": entry_name=domainapp+" "+entry_name
            obj.recursive_mkdir(obj.datapath, entry_name, obj.lineindex+1)
            obj.handle_entry(entry_name, start_phrase=phrases[0], end_phrase="[/entry]" if phrases[0]=="[entry]" else "end_entry")
        elif phrases[0]=="set_options":
            obj.check_enough_args(phrases, 2)
            obj.handle_set_global_options(obj.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split())
        elif phrases[0].startswith("setvar:"): 
            obj.check_enough_args(phrases, 2)
            obj.handle_set_variable(obj.lines_data[obj.lineindex])
        elif phrases[0]==end_phrase:
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.handle_end_section("entries")
            # deprecation warning
            if phrases[0]=="end_main":
                obj.handle_warning(obj.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=str(obj.lineindex+1), old_phrase="end_main", new_phrase=r"{/entries_section}"))
            break
        else: obj.handle_error(obj.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(obj.lineindex+1)))
    ## END --Process entries/main block--
