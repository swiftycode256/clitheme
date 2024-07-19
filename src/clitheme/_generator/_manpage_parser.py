# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
substrules_section parser function (internal module)
"""
import os
import sys
from typing import Optional
from .. import _globalvar
from . import _dataclass

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_manpage_section(obj: _dataclass.GeneratorObject, first_phrase: str):
    obj.handle_begin_section("manpage")
    end_phrase="{/manpage_section}"
    while obj.goto_next_line():
        phrases=obj.lines_data[obj.lineindex].split()
        def get_file_content(filepath: list) -> str:
            # determine file path
            parent_dir=""
            # if no filename provided, use current working directory as parent path; else, use the directory the file is in as the parent path
            if obj.filename.strip()!="":
                parent_dir+=os.path.dirname(obj.filename)
            file_dir=parent_dir+("/" if parent_dir!="" else "")+_globalvar.splitarray_to_string(filepath).replace(" ","/")
            # get file content
            filecontent: str
            try: filecontent=open(file_dir, 'r', encoding="utf-8").read()
            except: obj.handle_error(obj.fd.feof("include-file-read-error", "Line {num}: unable to read file \"{filepath}\":\n{error_msg}", num=str(obj.lineindex+1), filepath=obj.fmt(file_dir), error_msg=sys.exc_info()[1]))
            # write manpage files in theme-info for db migration feature to work successfully
            obj.write_manpage_file(filepath, filecontent, -1, custom_parent_path=obj.path+"/"+_globalvar.generator_info_pathname+"/"+obj.custom_infofile_name+"/manpage_data")
            return filecontent
        if phrases[0]=="[file_content]":
            def handle(p: list) -> list:
                obj.check_enough_args(p, 2)
                filepath=obj.subst_variable_content(_globalvar.splitarray_to_string(p[1:])).split()
                # sanity check the file path
                if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                    obj.handle_error(obj.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                return filepath
            file_paths=[handle(phrases)]
            # handle additional [file_content] phrases
            prev_line_index=obj.lineindex
            while obj.goto_next_line():
                p=obj.lines_data[obj.lineindex].split()
                if p[0]=="[file_content]":
                    prev_line_index=obj.lineindex
                    file_paths.append(handle(p))
                else:
                    obj.lineindex=prev_line_index
                    break
            content=obj.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/file_content]")
            for filepath in file_paths:
                obj.write_manpage_file(filepath, content, obj.lineindex+1)
        elif phrases[0]=="include_file":
            obj.check_enough_args(phrases, 2)
            filepath=obj.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split()
            if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                obj.handle_error(obj.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))

            filecontent=get_file_content(filepath)
            # expect "as" clause on next line
            if obj.goto_next_line() and len(obj.lines_data[obj.lineindex].split())>0 and obj.lines_data[obj.lineindex].split()[0]=="as":
                target_file=obj.subst_variable_content(_globalvar.splitarray_to_string(obj.lines_data[obj.lineindex].split()[1:])).split()
                if _globalvar.sanity_check(_globalvar.splitarray_to_string(target_file))==False:
                    obj.handle_error(obj.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                obj.write_manpage_file(target_file, filecontent, obj.lineindex+1)
            else:
                obj.handle_error(obj.fd.feof("include-file-missing-phrase-err", "Missing \"as <filename>\" phrase on next line of line {num}", num=str(obj.lineindex+1-1)))
        elif phrases[0]=="[include_file]":
            obj.check_enough_args(phrases, 2)
            filepath=obj.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split()
            if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                obj.handle_error(obj.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
            filecontent=get_file_content(filepath)
            while obj.goto_next_line():
                p=obj.lines_data[obj.lineindex].split()
                if p[0]=="as":
                    obj.check_enough_args(p, 2)
                    target_file=obj.subst_variable_content(_globalvar.splitarray_to_string(obj.lines_data[obj.lineindex].split()[1:])).split()
                    if _globalvar.sanity_check(_globalvar.splitarray_to_string(target_file))==False:
                        obj.handle_error(obj.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=str(obj.lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    obj.write_manpage_file(target_file, filecontent, obj.lineindex+1)
                elif p[0]=="[/include_file]":
                    obj.check_extra_args(p, 1, use_exact_count=True)
                    break
                else: obj.handle_invalid_phrase(phrases[0])
        elif phrases[0]=="set_options":
            obj.check_enough_args(phrases, 2)
            obj.handle_set_global_options(obj.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split())
        elif phrases[0].startswith("setvar:"): 
            obj.check_enough_args(phrases, 2)
            obj.handle_set_variable(obj.lines_data[obj.lineindex])
        elif phrases[0]==end_phrase:
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.handle_end_section("manpage")
            break
        else: obj.handle_invalid_phrase(phrases[0])
