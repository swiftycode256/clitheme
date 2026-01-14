# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Functions for data processing and error handling (internal module)
"""
import os
import gzip
from typing import Optional, List
from .. import _globalvar, _frontend_internal as frontend
from . import syntax_error

class DataHandlers:
    def __init__(self, path: str):
        self.path=path
        self.success=True
        self.messages: List[str]=[]
        if not os.path.exists(self.path): os.mkdir(self.path)
        self.datapath=self.path+"/"+_globalvar.generator_data_pathname
        if not os.path.exists(self.datapath): os.mkdir(self.datapath)
        self.fd=frontend.FetchDescriptor(domain_name=_globalvar.fd_domain_name, app_name=_globalvar.fd_app_name, subsections="generator")
        self.fmt=_globalvar.make_printable # alias for the make_printable function
    def handle_error(self, message: str):
        output=self.fd.feof("error-prefix", "Error: {msg}", msg=message)
        self.success=False
        self.messages.append(output)
    def handle_syntax_error(self, message: str, no_prefix: bool=False):
        output=message if no_prefix else self.fd.feof("syntax-error-prefix", "Syntax error: {msg}", msg=message)
        self.success=False
        self.messages.append(output)
        raise syntax_error(output)
    def handle_warning(self, message: str):
        output=self.fd.feof("warning-str", "Warning: {msg}", msg=message)
        self.messages.append(output)
    def recursive_mkdir(self, path: str, entry_name: str, line_number_debug: str) -> bool:
        # recursively generate directories (excluding file itself)
        current_path=path
        current_entry="" # for error output
        for x in entry_name.split()[:-1]:
            current_entry+=x+" "
            current_path+="/"+x
            if os.path.isfile(current_path): # conflict with entry file
                self.handle_error(self.fd.feof("subsection-conflict-err", "Line {num}: Cannot create subsection \"{name}\" because an entry with the same name already exists", \
                    num=line_number_debug, name=self.fmt(current_entry.strip())))
                return False
            elif os.path.isdir(str(current_path))==False: # directory does not exist
                os.mkdir(current_path) 
        return True
    def add_entry(self, path: str, entry_name: str, entry_content: str, line_number_debug: str): # add entry to where it belongs
        if not self.recursive_mkdir(path, entry_name, line_number_debug): return
        target_path=path
        for x in entry_name.split():
            target_path+="/"+x
        if os.path.isdir(target_path):
            self.handle_error(self.fd.feof("entry-conflict-err", "Line {num}: Cannot create entry \"{name}\" because a subsection with the same name already exists", \
                num=line_number_debug, name=self.fmt(entry_name)))
        else:
            if os.path.isfile(target_path):
                self.handle_warning(self.fd.feof("repeated-entry-warn", "Line {num}: Repeated entry \"{name}\", overwriting", \
                    num=line_number_debug, name=self.fmt(entry_name)))
            f=open(target_path,'w', encoding="utf-8")
            f.write(entry_content+"\n")
    def write_infofile(self, path: str, filename: str, content: str, line_number_debug: int, header_name_debug: str):
        if not os.path.isdir(path):
            os.makedirs(path)
        target_path=path+"/"+filename
        if os.path.isfile(target_path):
            self.handle_warning(self.fd.feof("repeated-header-warn", "Line {num}: Repeated header info \"{name}\", overwriting", \
                num=str(line_number_debug), name=self.fmt(header_name_debug)))
        f=open(target_path,'w', encoding="utf-8")
        f.write(content+'\n')
    def write_infofile_newlines(self, path: str, filename: str, content_phrases: List[str], line_number_debug: int, header_name_debug: str):
        if not os.path.isdir(path):
            os.makedirs(path)
        target_path=path+"/"+filename
        if os.path.isfile(target_path):
            self.handle_warning(self.fd.feof("repeated-header-warn", "Line {num}: Repeated header info \"{name}\", overwriting", \
                num=str(line_number_debug), name=self.fmt(header_name_debug)))
        f=open(target_path,'w', encoding="utf-8")
        for line in content_phrases:
            f.write(line+"\n")
    def write_manpage_file(self, file_path: List[str], content: str, line_number_debug: int, custom_parent_path: Optional[str]=None):
        parent_path=custom_parent_path if custom_parent_path!=None else self.path+"/"+_globalvar.generator_manpage_pathname
        parent_path+='/'+os.path.dirname(' '.join(file_path).replace(" ","/"))
        # create the parent directory
        try: os.makedirs(parent_path, exist_ok=True)
        except (FileExistsError, NotADirectoryError):
            self.handle_error(self.fd.feof("manpage-subdir-file-conflict-err", "Line {num}: Conflicting files and subdirectories; please check previous definitions", num=str(line_number_debug)))
        else:
            full_path=parent_path+"/"+file_path[-1]
            if os.path.isfile(full_path):
                if line_number_debug!=-1: self.handle_warning(self.fd.feof("repeated-manpage-warn","Line {num}: Repeated manpage file, overwriting", num=str(line_number_debug)))
            try:
                # write the compressed and original version of the file
                open(full_path, "w", encoding="utf-8").write(content)
                open(full_path+".gz", "wb").write(gzip.compress(bytes(content, "utf-8")))
            except IsADirectoryError:
                self.handle_error(self.fd.feof("manpage-subdir-file-conflict-err", "Line {num}: Conflicting files and subdirectories; please check previous definitions", num=str(line_number_debug)))