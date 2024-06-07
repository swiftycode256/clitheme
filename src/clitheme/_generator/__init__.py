# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Generator function used in applying themes (should not be invoked directly)
"""
import os
import string
import random
from typing import Optional

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
    obj=_dataclass.GeneratorObject(file_content=file_content, custom_infofile_name=custom_infofile_name, filename=filename, path=path, silence_warn=silence_warn)

    ## Main code
    while obj.lineindex<len(obj.lines_data)-1:
        obj.lineindex+=1
        # ignore empty and comment lines
        if obj.is_ignore_line(): continue
        first_phrase=obj.lines_data[obj.lineindex].split()[0]
        # process header and main sections here
        if first_phrase=="set_options":
            obj.check_enough_args(obj.lines_data[obj.lineindex].split(), 2)
            obj.handle_set_global_options(obj.subst_variable_content(_globalvar.splitarray_to_string(obj.lines_data[obj.lineindex].split()[1:])).split(), really_really_global=True)
        elif first_phrase.startswith("setvar:"): 
            obj.check_enough_args(obj.lines_data[obj.lineindex].split(), 2)
            obj.handle_set_variable(obj.lines_data[obj.lineindex], really_really_global=True)
        elif first_phrase=="begin_header" or first_phrase==r"{header_section}":
            _header_parser.handle_header_section(obj, first_phrase)
        elif first_phrase=="begin_main" or first_phrase==r"{entries_section}":
            _entries_parser.handle_entries_section(obj, first_phrase)
        elif first_phrase==r"{substrules_section}":
            _substrules_parser.handle_substrules_section(obj, first_phrase)
        elif first_phrase==r"{manpage_section}":
            _manpage_parser.handle_manpage_section(obj, first_phrase)
        else: obj.handle_error(obj.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=first_phrase, num=str(obj.lineindex+1)))

    if obj.section_parsing or not "header" in obj.parsed_sections or (not "entries" in obj.parsed_sections and not "substrules" in obj.parsed_sections and not "manpage" in obj.parsed_sections):
        obj.handle_error(obj.fd.reof("incomplete-section-err", "Missing or incomplete header or content sections"))
    # record file content for database migration/upgrade feature
    obj.write_infofile(obj.path+"/"+_globalvar.generator_info_pathname+"/"+obj.custom_infofile_name, "file_content", obj.file_content, obj.lineindex+1, "<file_content>")
    # record *full* file path for update-themes feature
    obj.write_infofile(obj.path+"/"+_globalvar.generator_info_pathname+"/"+obj.custom_infofile_name, _globalvar.generator_info_filename.format(info="filepath"), os.path.abspath(filename), obj.lineindex+1, "<filepath>")
    # Update current theme index
    theme_index=open(obj.path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename, 'w', encoding="utf-8")
    theme_index.write(obj.custom_infofile_name+"\n")
    path=obj.path
    return obj.path

# prevent circular import error
from .. import _globalvar
from . import _dataclass
from . import _header_parser, _entries_parser, _substrules_parser, _manpage_parser
_globalvar.handle_set_themedef(_dataclass.GeneratorObject.frontend, "generator")