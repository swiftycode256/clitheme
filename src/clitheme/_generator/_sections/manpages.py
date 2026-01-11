# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
substrules_section parser function (internal module)
"""
import os
import sys
from typing import List
from ... import _globalvar
from .. import _parser_handlers

def handle_manpage_section(self: _parser_handlers.GeneratorObject, end_phrase: str):
    self.handle_begin_section("manpages")
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        def get_file_content(filepath: List[str]) -> str:
            # determine file path
            parent_dir=""
            # if no filename provided, use current working directory as parent path; else, use the directory the file is in as the parent path
            if self.filename.strip()!="":
                parent_dir+=os.path.dirname(self.filename)
            file_dir=parent_dir+("/" if parent_dir!="" else "")+' '.join(filepath).replace(" ","/")
            # get file content
            orig_stdout=sys.stdout
            sys.stdout=sys.__stdout__
            is_stdin=_globalvar.handle_stdin_prompt(file_dir)
            filecontent: str
            try: filecontent=open(file_dir, 'r', encoding="utf-8").read()
            except:
                self.handle_error(self.fd.feof("include-file-read-err", "Line {num}: unable to read file \"{filepath}\":\n{error_msg}", num=self.linenum(), filepath=self.fmt(file_dir), error_msg=self.fmt(str(sys.exc_info()[1]))))
                return ""
            else:
                if is_stdin: print()
                # write manpage files in theme-info for db migration feature to work successfully
                self.write_manpage_file(filepath, filecontent, -1, custom_parent_path=self.path+"/"+_globalvar.generator_info_pathname+"/"+self.custom_infofile_name+"/manpage_data")
                return filecontent
            finally: sys.stdout=orig_stdout
        if phrases[0]=="[file_content]":
            def handle(p: List[str]) -> List[str]:
                self.check_enough_args(p, 2)
                filepath=self.parse_content(' '.join(p[1:]), pure_name=True).split()
                # sanity check the file path
                if _globalvar.sanity_check(' '.join(filepath))==False:
                    self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    filepath=[_globalvar.sanitize_str(p) for p in filepath]
                return filepath
            file_paths=[handle(phrases)]
            # handle additional [file_content] phrases
            prev_line_index=self.lineindex
            while self.goto_next_line():
                p=self.get_current_line().split()
                if p[0]=="[file_content]":
                    prev_line_index=self.lineindex
                    file_paths.append(handle(p))
                else:
                    self.lineindex=prev_line_index
                    break
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/file_content]")
            for filepath in file_paths:
                self.write_manpage_file(filepath, content, self.linenum())
        elif phrases[0] in ("<include_file>", "include_file"):
            self.check_enough_args(phrases, 2)
            filepath=self.parse_content(' '.join(phrases[1:]), pure_name=True).split()
            if _globalvar.sanity_check(' '.join(filepath))==False:
                self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                filepath=[_globalvar.sanitize_str(p) for p in filepath]

            filecontent=get_file_content(filepath)
            # expect "as" clause on next line
            if self.goto_next_line() and self.get_current_line().split()[0] in ("as:", "as"):
                target_file=self.parse_content(' '.join(self.get_current_line().split()[1:]), pure_name=True).split()
                if _globalvar.sanity_check(' '.join(target_file))==False:
                    self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    target_file=[_globalvar.sanitize_str(p) for p in target_file]
                self.write_manpage_file(target_file, filecontent, self.linenum())
            else:
                self.handle_error(self.fd.feof("include-file-missing-phrase-err", "Missing \"as <filename>\" phrase on next line of line {num}", num=str(self.linenum()-1)))
                self.lineindex-=1
        elif phrases[0]=="[include_file]":
            self.check_enough_args(phrases, 2)
            filepath=self.parse_content(' '.join(phrases[1:]), pure_name=True).split()
            if _globalvar.sanity_check(' '.join(filepath))==False:
                self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                filepath=[_globalvar.sanitize_str(p) for p in filepath]
            filecontent=get_file_content(filepath)
            while self.goto_next_line():
                p=self.get_current_line().split()
                if p[0] in ("as:", "as"):
                    self.check_enough_args(p, 2)
                    target_file=self.parse_content(' '.join(self.get_current_line().split()[1:]), pure_name=True).split()
                    if _globalvar.sanity_check(' '.join(target_file))==False:
                        self.handle_error(self.fd.feof("sanity-check-manpage-err", "Line {num}: manpage paths {sanitycheck_msg}; use spaces to denote subdirectories", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                        target_file=[_globalvar.sanitize_str(p) for p in target_file]
                    self.write_manpage_file(target_file, filecontent, self.linenum())
                elif p[0]=="[/include_file]":
                    self.check_extra_args(p, 1)
                    break
                else: self.handle_invalid_phrase(phrases[0])
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1)
            self.handle_end_section("manpages")
            break
        else: self.handle_invalid_phrase(phrases[0])
    else: self.handle_unterminated_section("manpages")
