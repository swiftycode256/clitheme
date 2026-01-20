# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from ... import _globalvar
from .. import _parser_handlers

def handle_entries_section(self: _parser_handlers.GeneratorObject, end_phrase: str):
    self.handle_begin_section("entries")
    self.in_domainapp=""
    self.in_subsection=""
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        if phrases[0] in ("<in_domainapp>", "in_domainapp"):
            self.check_enough_args(phrases, 3)
            self.check_extra_args(phrases, 3)
            this_phrases=self.parse_content(_globalvar.extract_content(self.get_current_line()), pure_name=True).split()
            assert len(this_phrases)==2
            self.in_domainapp=' '.join(this_phrases) # Remove extra spaces
            if _globalvar.sanity_check(self.in_domainapp)==False:
                self.handle_error(self.fd.feof("sanity-check-domainapp-err", "Line {num}: Domain and app names {sanitycheck_msg}", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                self.in_domainapp=_globalvar.sanitize_str(self.in_domainapp)
            self.in_subsection="" # clear subsection
        elif phrases[0] in ("<in_subsection>", "in_subsection"):
            self.check_enough_args(phrases, 2)
            self.in_subsection=self.parse_content(_globalvar.extract_content(self.get_current_line()), pure_name=True)
            self.in_subsection=' '.join(self.in_subsection.split()) # Remove extra spaces
            if _globalvar.sanity_check(self.in_subsection)==False:
                self.handle_error(self.fd.feof("sanity-check-subsection-err", "Line {num}: Subsection names {sanitycheck_msg}", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                self.in_subsection=_globalvar.sanitize_str(self.in_subsection)
        elif phrases[0] in ("<unset_domainapp>", "unset_domainapp"):
            self.check_extra_args(phrases, 1)
            self.in_domainapp=""; self.in_subsection=""
        elif phrases[0] in ("<unset_subsection>", "unset_subsection"):
            self.check_extra_args(phrases, 1)
            self.in_subsection=""
        elif phrases[0] in ("[entry]", "entry"):
            self.handle_entry(start_phrase=phrases[0], end_phrase="[/entry]" if phrases[0]=="[entry]" else "end_entry")
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1)
            self.handle_end_section("entries")
            # deprecation warning
            if phrases[0]=="end_main":
                self.handle_warning(self.fd.feof("syntax-phrase-deprecation-warn", "Line {num}: Phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=self.linenum(), old_phrase="end_main", new_phrase=r"{/entries}"))
            break
        else: self.handle_invalid_phrase(phrases[0])
    else: self.handle_unterminated_section("entries")
