# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Functions for data processing and error handling (internal module)
"""
import os
import gzip
from typing import Optional, List
from .. import _globalvar, frontend

# spell-checker:ignore datapath

class DataHandlers:
    frontend=frontend

    def __init__(self, path: str, silence_warn: bool):
        self.path=path
        self.silence_warn=silence_warn
        if not os.path.exists(self.path): os.mkdir(self.path)
        self.datapath=self.path+"/"+_globalvar.generator_data_pathname
        if not os.path.exists(self.datapath): os.mkdir(self.datapath)
        self.fd=self.frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="generator")
        self.fmt=_globalvar.make_printable # alias for the make_printable function
    def handle_error(self, message: str, not_syntax_error: bool=False):
        output=message if not_syntax_error else self.fd.feof("error-str", "Syntax error: {msg}", msg=message)
        raise SyntaxError(output)
    def handle_warning(self, message: str):
        output=self.fd.feof("warning-str", "Warning: {msg}", msg=message)
        if not self.silence_warn: print(output)
    def recursive_mkdir(self, path: str, entry_name: str, line_number_debug: str): # recursively generate directories (excluding file itself)
        current_path=path
        current_entry="" # for error output
        for x in entry_name.split()[:-1]:
            current_entry+=x+" "
            current_path+="/"+x
            if os.path.isfile(current_path): # conflict with entry file
                self.handle_error(self.fd.feof("subsection-conflict-err", "Line {num}: cannot create subsection \"{name}\" because an entry with the same name already exists", \
                    num=line_number_debug, name=self.fmt(current_entry)))
            elif os.path.isdir(str(current_path))==False: # directory does not exist
                os.mkdir(current_path) 
    def add_entry(self, path: str, entry_name: str, entry_content: str, line_number_debug: str): # add entry to where it belongs
        self.recursive_mkdir(path, entry_name, line_number_debug)
        target_path=path
        for x in entry_name.split():
            target_path+="/"+x
        if os.path.isdir(target_path):
            self.handle_error(self.fd.feof("entry-conflict-err", "Line {num}: cannot create entry \"{name}\" because a subsection with the same name already exists", \
                num=line_number_debug, name=self.fmt(entry_name)))
        elif os.path.isfile(target_path):
            self.handle_warning(self.fd.feof("repeated-entry-warn", "Line {num}: repeated entry \"{name}\", overwriting", \
                num=line_number_debug, name=self.fmt(entry_name)))
        f=open(target_path,'w', encoding="utf-8")
        f.write(entry_content+"\n")
    def write_infofile(self, path: str, filename: str, content: str, line_number_debug: int, header_name_debug: str):
        if not os.path.isdir(path):
            os.makedirs(path)
        target_path=path+"/"+filename
        if os.path.isfile(target_path):
            self.handle_warning(self.fd.feof("repeated-header-warn", "Line {num}: repeated header info \"{name}\", overwriting", \
                num=str(line_number_debug), name=self.fmt(header_name_debug)))
        f=open(target_path,'w', encoding="utf-8")
        f.write(content+'\n')
    def write_infofile_newlines(self, path: str, filename: str, content_phrases: List[str], line_number_debug: int, header_name_debug: str):
        if not os.path.isdir(path):
            os.makedirs(path)
        target_path=path+"/"+filename
        if os.path.isfile(target_path):
            self.handle_warning(self.fd.feof("repeated-header-warn", "Line {num}: repeated header info \"{name}\", overwriting", \
                num=str(line_number_debug), name=self.fmt(header_name_debug)))
        f=open(target_path,'w', encoding="utf-8")
        for line in content_phrases:
            f.write(line+"\n")
    def write_manpage_file(self, file_path: List[str], content: str, line_number_debug: int, custom_parent_path: Optional[str]=None):
        parent_path=custom_parent_path if custom_parent_path!=None else self.path+"/"+_globalvar.generator_manpage_pathname
        parent_path+='/'+os.path.dirname(_globalvar.splitarray_to_string(file_path).replace(" ","/"))
        # create the parent directory
        try: os.makedirs(parent_path, exist_ok=True)
        except (FileExistsError, NotADirectoryError):
            self.handle_error(self.fd.feof("manpage-subdir-file-conflict-err", "Line {num}: conflicting files and subdirectories; please check previous definitions", num=str(line_number_debug)), not_syntax_error=True)
        full_path=parent_path+"/"+file_path[-1]
        if os.path.isfile(full_path):
            if line_number_debug!=-1: self.handle_warning(self.fd.feof("repeated-manpage-warn","Line {num}: repeated manpage file, overwriting", num=str(line_number_debug)))
        try:
            # write the compressed and original version of the file
            open(full_path, "w", encoding="utf-8").write(content)
            open(full_path+".gz", "wb").write(gzip.compress(bytes(content, "utf-8")))
        except IsADirectoryError:
            self.handle_error(self.fd.feof("manpage-subdir-file-conflict-err", "Line {num}: conflicting files and subdirectories; please check previous definitions", num=str(line_number_debug)), not_syntax_error=True)