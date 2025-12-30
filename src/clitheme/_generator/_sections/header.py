# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
header_section parser function (internal module)
"""
import re
from ... import _globalvar
from .. import _parser_handlers
from typing import Optional

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_header_section(self: _parser_handlers.GeneratorObject, end_phrase: str):
    self.handle_begin_section("header")
    name_specified=True
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        last_match: Optional[re.Match]=None
        def match_first_phrase(pattern: str) -> Optional[re.Match]:
            # Stores the match object into a variable
            nonlocal last_match
            last_match=re.fullmatch(pattern, phrases[0])
            return last_match
        if match_first_phrase(r"(name|version|description)(:)?")!=None:
            self.check_enough_args(phrases, 2)
            assert last_match!=None
            entry=last_match.group(1)
            content=self.parse_content(_globalvar.extract_content(self.get_current_line()),
                    pure_name=True,
                    preserve_indents=entry in ('name', 'description'))
            self.write_infofile(
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name,
                _globalvar.generator_info_filename.format(info=entry),
                content,self.linenum(),entry) # e.g. [...]/theme-info/1/clithemeinfo_name
            if entry=="name": name_specified=True
        elif match_first_phrase(r"(locales|supported_apps)(:)?")!=None:
            self.check_enough_args(phrases, 2)
            assert last_match!=None
            entry=last_match.group(1)
            content=self.parse_content(' '.join(phrases[1:]), pure_name=True).split()
            self.write_infofile_newlines(
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name,
                _globalvar.generator_info_v2filename.format(info=entry),
                content,self.linenum(),entry) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
        elif phrases[0] in ("[locales]", "[supported_apps]", "[description]", "locales_block", "supported_apps_block", "description_block"):
            self.check_extra_args(phrases, 1)
            # handle block input
            endphrase="end_block"
            if not phrases[0].endswith("_block"): endphrase=phrases[0].replace("[", "[/")

            is_description=phrases[0] in ("description_block", "[description]")
            content=self.handle_block_input(preserve_indents=is_description, preserve_empty_lines=is_description, end_phrase=endphrase, disable_char_subst=True)
            file_name=(_globalvar.generator_info_filename \
                        if is_description else \
                        _globalvar.generator_info_v2filename) \
                .format(info=re.sub(r'_block$', '', phrases[0]).replace('[','').replace(']',''))
            self.write_infofile(
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name,
                file_name,
                content,self.linenum(),re.sub(r'_block$','',phrases[0])) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1)
            if not name_specified:
                self.handle_error(self.fd.feof("missing-info-err", "{sect_name} section missing required entries: {entries}", sect_name="header", entries="name"))
            self.handle_end_section("header")
            break
        else: self.handle_invalid_phrase(phrases[0])
    else: self.handle_unterminated_section("header")