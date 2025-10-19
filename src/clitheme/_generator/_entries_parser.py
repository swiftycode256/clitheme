# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
entries_section parser function (internal module)
"""
from .. import _globalvar
from . import _parser_handlers

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_entries_section(obj: _parser_handlers.GeneratorObject, first_phrase: str):
    obj.handle_begin_section("entries")
    end_phrase="end_main" if first_phrase=="begin_main" else r"{/entries_section}"
    if first_phrase=="begin_main":
        obj.handle_warning(obj.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=obj.linenum(), old_phrase="begin_main", new_phrase=r"{entries_section}"))
    obj.in_domainapp=""
    obj.in_subsection=""
    while obj.goto_next_line():
        phrases=obj.lines_data[obj.lineindex].split()
        if phrases[0]=="in_domainapp":
            this_phrases=obj.parse_content(obj.lines_data[obj.lineindex].strip(), pure_name=True).split()
            obj.check_enough_args(this_phrases, 3)
            obj.check_extra_args(this_phrases, 3, use_exact_count=False)
            obj.in_domainapp=this_phrases[1]+" "+this_phrases[2]
            if _globalvar.sanity_check(obj.in_domainapp)==False:
                obj.handle_error(obj.fd.feof("sanity-check-domainapp-err", "Line {num}: domain and app names {sanitycheck_msg}", num=obj.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
            obj.in_subsection="" # clear subsection
        elif phrases[0]=="in_subsection":
            obj.check_enough_args(phrases, 2)
            obj.in_subsection=_globalvar.splitarray_to_string(phrases[1:])
            obj.in_subsection=obj.parse_content(obj.in_subsection, pure_name=True)
            if _globalvar.sanity_check(obj.in_subsection)==False:
                obj.handle_error(obj.fd.feof("sanity-check-subsection-err", "Line {num}: subsection names {sanitycheck_msg}", num=obj.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
        elif phrases[0]=="unset_domainapp":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.in_domainapp=""; obj.in_subsection=""
        elif phrases[0]=="unset_subsection":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.in_subsection=""
        elif phrases[0] in ("entry", "[entry]"):
            obj.check_enough_args(phrases, 2)
            entry_name=_globalvar.extract_content(obj.lines_data[obj.lineindex])
            obj.handle_entry(entry_name, start_phrase=phrases[0], end_phrase="[/entry]" if phrases[0]=="[entry]" else "end_entry")
        elif obj.handle_setters(): pass
        elif phrases[0]==end_phrase:
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.handle_end_section("entries")
            # deprecation warning
            if phrases[0]=="end_main":
                obj.handle_warning(obj.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=obj.linenum(), old_phrase="end_main", new_phrase=r"{/entries_section}"))
            break
        else: obj.handle_invalid_phrase(phrases[0])
