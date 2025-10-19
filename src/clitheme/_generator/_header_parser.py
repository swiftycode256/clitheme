# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
header_section parser function (internal module)
"""
import re
from .. import _globalvar
from . import _parser_handlers

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_header_section(self: _parser_handlers.GeneratorObject, first_phrase: str):
    self.handle_begin_section("header")
    end_phrase="end_header" if first_phrase=="begin_header" else r"{/header_section}"
    specified_info=[]
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        if phrases[0] in ("name", "version", "description"):
            self.check_enough_args(phrases, 2)
            content=_globalvar.extract_content(self.get_current_line())
            content=self.parse_content(content, pure_name=phrases[0]!="description")
            self.write_infofile( \
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name, \
                _globalvar.generator_info_filename.format(info=phrases[0]),\
                content,self.lineindex+1,phrases[0]) # e.g. [...]/theme-info/1/clithemeinfo_name
        elif phrases[0] in ("locales", "supported_apps"):
            self.check_enough_args(phrases, 2)
            content=self.parse_content(_globalvar.splitarray_to_string(phrases[1:]), pure_name=True).split()
            self.write_infofile_newlines( \
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name, \
                _globalvar.generator_info_v2filename.format(info=phrases[0]),\
                content,self.lineindex+1,phrases[0]) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
        elif phrases[0] in ("locales_block", "supported_apps_block", "description_block", "[locales]", "[supported_apps]", "[description]"):
            self.check_extra_args(phrases, 1, use_exact_count=True)
            # handle block input
            content=""; file_name=""
            endphrase="end_block"
            if not phrases[0].endswith("_block"): endphrase=phrases[0].replace("[", "[/")
            if phrases[0] in ("description_block", "[description]"):
                content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase=endphrase)
                file_name=_globalvar.generator_info_filename.format(info=re.sub(r'_block$', '', phrases[0]).replace('[','').replace(']',''))
            else:
                content=self.handle_block_input(preserve_indents=False, preserve_empty_lines=False, end_phrase=endphrase, disable_substesc=True)
                file_name=_globalvar.generator_info_v2filename.format(info=re.sub(r'_block$', '', phrases[0]).replace('[','').replace(']',''))
            self.write_infofile( \
                self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name, \
                file_name,\
                content,self.lineindex+1,re.sub(r'_block$','',phrases[0])) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1, use_exact_count=True)
            if not "name" in specified_info:
                self.handle_error(self.fd.feof("missing-info-err", "{sect_name} section missing required entries: {entries}", sect_name="header", entries="name"))
            self.handle_end_section("header")
            break
        else: self.handle_invalid_phrase(phrases[0])
        specified_info.append(phrases[0])