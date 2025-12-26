# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Generator function used in applying themes (should not be invoked directly)
"""
import os
import string
import random

from ._sections import entries, header, manpage
from .. import _globalvar
from . import _parser_handlers
from ._sections import substrules

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

path=""
silence_warn=False
__all__=["generate_data_hierarchy"]

def generate_custom_path() -> str:
    # Generate a temporary path
    global path
    path=_globalvar.clitheme_temp_root+"/clitheme-temp-"
    for x in range(8):
        path+=random.choice(string.ascii_letters)
    return path


def generate_data_hierarchy(file_content: str, custom_path_gen=True, custom_infofile_name="1", filename: str="") -> str:
    # make directories
    if custom_path_gen:
        generate_custom_path()
    global path
    self=_parser_handlers.GeneratorObject(file_content=file_content, custom_infofile_name=custom_infofile_name, filename=filename, path=path, silence_warn=silence_warn)

    before_content_lines=True
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        first_phrase=phrases[0]
        is_content=True
        if first_phrase in ("begin_header", r"{header_section}"):
            self.check_extra_args(phrases, 1)
            header.handle_header_section(self, first_phrase)
        elif first_phrase in ("begin_main", r"{entries_section}"):
            self.check_extra_args(phrases, 1)
            entries.handle_entries_section(self, first_phrase)
        elif first_phrase==r"{substrules_section}":
            self.check_extra_args(phrases, 1)
            substrules.handle_substrules_section(self, first_phrase)
        elif first_phrase==r"{manpage_section}":
            self.check_extra_args(phrases, 1)
            manpage.handle_manpage_section(self, first_phrase)
        elif self.handle_setters(really_really_global=True): pass
        elif first_phrase=="!require_version":
            is_content=False
            self.check_enough_args(phrases, 2)
            self.check_extra_args(phrases, 2)
            if not before_content_lines:
                self.handle_error(self.fd.feof("phrase-precedence-err", "Line {num}: header macro \"{phrase}\" must be specified before other lines", num=self.linenum(), phrase=first_phrase))
            self.check_version(phrases[1])
        else: self.handle_invalid_phrase(first_phrase)

        if is_content: before_content_lines=False

    def is_content_parsed() -> bool:
        content_sections=["entries", "substrules", "manpage"]
        for section in content_sections:
            if section in self.parsed_sections: return True
        return False
    if self.section_parsing or not "header" in self.parsed_sections or not is_content_parsed():
        self.handle_error(self.fd.reof("incomplete-section-err", "Missing or incomplete header or content sections"))
    # record file content for database migration/upgrade feature
    self.write_infofile(self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name, "file_content", self.file_content, self.linenum(), "<file_content>")
    # record *full* file path for update-themes feature
    self.write_infofile(self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name, _globalvar.generator_info_filename.format(info="filepath"), os.path.abspath(filename), self.linenum(), "<filepath>")
    # Update current theme index
    theme_index=open(self.path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename, 'w', encoding="utf-8")
    theme_index.write(self.custom_infofile_name+"\n")
    path=self.path
    return self.path
