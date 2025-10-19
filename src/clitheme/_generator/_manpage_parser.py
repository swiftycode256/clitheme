# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
substrules_section parser function (internal module)
"""
import os
import sys
from typing import Optional, List
from .. import _globalvar
from . import _parser_handlers

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_manpage_section(self: _parser_handlers.GeneratorObject, first_phrase: str):
    self.handle_begin_section("manpage")
    end_phrase="{/manpage_section}"
    while self.goto_next_line():
        phrases=self.lines_data[self.lineindex].split()
        def get_file_content(filepath: List[str]) -> str:
            # determine file path
            parent_dir=""
            # if no filename provided, use current working directory as parent path; else, use the directory the file is in as the parent path
            if self.filename.strip()!="":
                parent_dir+=os.path.dirname(self.filename)
            file_dir=parent_dir+("/" if parent_dir!="" else "")+_globalvar.splitarray_to_string(filepath).replace(" ","/")
            # get file content
            orig_stdout=sys.stdout
            sys.stdout=sys.__stdout__
            is_stdin=_globalvar.handle_stdin_prompt(file_dir)
            filecontent: str
            try: filecontent=open(file_dir, 'r', encoding="utf-8").read()
            except: self.handle_error(self.fd.feof("include-file-read-err", "Line {num}: unable to read file \"{filepath}\":\n{error_msg}", num=self.linenum(), filepath=self.fmt(file_dir), error_msg=sys.exc_info()[1]), not_syntax_error=True)
            if is_stdin: print()
            sys.stdout=orig_stdout
            # write manpage files in theme-info for db migration feature to work successfully
            self.write_manpage_file(filepath, filecontent, -1, custom_parent_path=self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name+"/manpage_data")
            return filecontent
        if phrases[0]=="[file_content]":
            def handle(p: List[str]) -> List[str]:
                self.check_enough_args(p, 2)
                filepath=self.parse_content(_globalvar.splitarray_to_string(p[1:]), pure_name=True).split()
                # sanity check the file path
                if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                    self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                return filepath
            file_paths=[handle(phrases)]
            # handle additional [file_content] phrases
            prev_line_index=self.lineindex
            while self.goto_next_line():
                p=self.lines_data[self.lineindex].split()
                if p[0]=="[file_content]":
                    prev_line_index=self.lineindex
                    file_paths.append(handle(p))
                else:
                    self.lineindex=prev_line_index
                    break
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/file_content]")
            for filepath in file_paths:
                self.write_manpage_file(filepath, content, self.lineindex+1)
        elif phrases[0]=="include_file":
            self.check_enough_args(phrases, 2)
            filepath=self.parse_content(_globalvar.splitarray_to_string(phrases[1:]), pure_name=True).split()
            if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))

            filecontent=get_file_content(filepath)
            # expect "as" clause on next line
            if self.goto_next_line() and len(self.lines_data[self.lineindex].split())>0 and self.lines_data[self.lineindex].split()[0]=="as":
                target_file=self.parse_content(_globalvar.splitarray_to_string(self.lines_data[self.lineindex].split()[1:]), pure_name=True).split()
                if _globalvar.sanity_check(_globalvar.splitarray_to_string(target_file))==False:
                    self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                self.write_manpage_file(target_file, filecontent, self.lineindex+1)
            else:
                self.handle_error(self.fd.feof("include-file-missing-phrase-err", "Missing \"as <filename>\" phrase on next line of line {num}", num=str(self.lineindex+1-1)))
        elif phrases[0]=="[include_file]":
            self.check_enough_args(phrases, 2)
            filepath=self.parse_content(_globalvar.splitarray_to_string(phrases[1:]), pure_name=True).split()
            if _globalvar.sanity_check(_globalvar.splitarray_to_string(filepath))==False:
                self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
            filecontent=get_file_content(filepath)
            while self.goto_next_line():
                p=self.lines_data[self.lineindex].split()
                if p[0]=="as":
                    self.check_enough_args(p, 2)
                    target_file=self.parse_content(_globalvar.splitarray_to_string(self.lines_data[self.lineindex].split()[1:]), pure_name=True).split()
                    if _globalvar.sanity_check(_globalvar.splitarray_to_string(target_file))==False:
                        self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    self.write_manpage_file(target_file, filecontent, self.lineindex+1)
                elif p[0]=="[/include_file]":
                    self.check_extra_args(p, 1, use_exact_count=True)
                    break
                else: self.handle_invalid_phrase(phrases[0])
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1, use_exact_count=True)
            self.handle_end_section("manpage")
            break
        else: self.handle_invalid_phrase(phrases[0])
