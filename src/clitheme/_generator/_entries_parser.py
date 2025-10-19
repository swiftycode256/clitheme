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

def handle_entries_section(self: _parser_handlers.GeneratorObject, first_phrase: str):
    self.handle_begin_section("entries")
    end_phrase="end_main" if first_phrase=="begin_main" else r"{/entries_section}"
    if first_phrase=="begin_main":
        self.handle_warning(self.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=self.linenum(), old_phrase="begin_main", new_phrase=r"{entries_section}"))
    self.in_domainapp=""
    self.in_subsection=""
    while self.goto_next_line():
        phrases=self.lines_data[self.lineindex].split()
        if phrases[0]=="in_domainapp":
            this_phrases=self.parse_content(self.lines_data[self.lineindex].strip(), pure_name=True).split()
            self.check_enough_args(this_phrases, 3)
            self.check_extra_args(this_phrases, 3, use_exact_count=False)
            self.in_domainapp=this_phrases[1]+" "+this_phrases[2]
            if _globalvar.sanity_check(self.in_domainapp)==False:
                self.handle_error(self.fd.feof("sanity-check-domainapp-err", "Line {num}: domain and app names {sanitycheck_msg}", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
            self.in_subsection="" # clear subsection
        elif phrases[0]=="in_subsection":
            self.check_enough_args(phrases, 2)
            self.in_subsection=_globalvar.splitarray_to_string(phrases[1:])
            self.in_subsection=self.parse_content(self.in_subsection, pure_name=True)
            if _globalvar.sanity_check(self.in_subsection)==False:
                self.handle_error(self.fd.feof("sanity-check-subsection-err", "Line {num}: subsection names {sanitycheck_msg}", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
        elif phrases[0]=="unset_domainapp":
            self.check_extra_args(phrases, 1, use_exact_count=True)
            self.in_domainapp=""; self.in_subsection=""
        elif phrases[0]=="unset_subsection":
            self.check_extra_args(phrases, 1, use_exact_count=True)
            self.in_subsection=""
        elif phrases[0] in ("entry", "[entry]"):
            self.check_enough_args(phrases, 2)
            entry_name=_globalvar.extract_content(self.lines_data[self.lineindex])
            self.handle_entry(entry_name, start_phrase=phrases[0], end_phrase="[/entry]" if phrases[0]=="[entry]" else "end_entry")
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1, use_exact_count=True)
            self.handle_end_section("entries")
            # deprecation warning
            if phrases[0]=="end_main":
                self.handle_warning(self.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=self.linenum(), old_phrase="end_main", new_phrase=r"{/entries_section}"))
            break
        else: self.handle_invalid_phrase(phrases[0])
