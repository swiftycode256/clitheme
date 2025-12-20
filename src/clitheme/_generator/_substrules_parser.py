# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
substrules_section parser function (internal module)
"""
import os
import copy
import re
import sys
from typing import Optional
from .. import _globalvar
from . import _parser_handlers, db_interface

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_substrules_section(self: _parser_handlers.GeneratorObject, first_phrase: str):
    self.handle_begin_section("substrules")
    end_phrase=r"{/substrules_section}"
    command_filters: Optional[list]=None
    command_filter_is_regex=False
    command_filter_strictness=0
    # If True, reset foregroundonly option to beforehand during next command filter
    outline_foregroundonly=None
    def reset_outline_foregroundonly():
        """
        Set foregroundonly option to false if foregroundonly option is "inline" and not enabled previously
        """
        nonlocal outline_foregroundonly
        if outline_foregroundonly!=None:
            self.global_options['foregroundonly']=outline_foregroundonly
            outline_foregroundonly=None
    def check_pattern(pattern: str, linenum: Optional[int]=None):
        try: re.compile(pattern)
        except re.error: self.handle_error(self.fd.feof("bad-cmd-filter-pattern-err", "Bad command filter pattern at line {num} ({error_msg})", num=str(linenum if linenum!=None else self.linenum()), error_msg=sys.exc_info()[1]))

    # initialize the database
    if os.path.exists(self.path+"/"+_globalvar.db_filename):
        try: db_interface.connect_db(path=self.path+"/"+_globalvar.db_filename)
        except db_interface.need_db_regenerate:
            from ..exec import _check_regenerate_db
            if not _check_regenerate_db(self.path): self.handle_error(self.fd.reof("db-regenerate-fail-err", "Failed to migrate existing substrules database; try performing the operation without using \"--overlay\""), not_syntax_error=True)
            db_interface.connect_db(path=self.path+"/"+_globalvar.db_filename)
    else: db_interface.init_db(self.path+"/"+_globalvar.db_filename)
    db_interface.debug_mode=not self.silence_warn
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        subst_pat=re.fullmatch(r"\[(?P<name>subst(itute)?_(string|regex))(\]|>>)", phrases[0])
        if subst_pat!=None:
            options={"effective_commands": copy.copy(command_filters),
                      "command_is_regex": command_filter_is_regex,
                      "is_regex": re.fullmatch(r"\[subst(itute)?_regex(\]|>>)", phrases[0])!=None,
                      "strictness": command_filter_strictness}
            self.handle_entry(
                start_phrase=f"[{subst_pat.group('name')}]",
                end_phrase=f"[/{subst_pat.group('name')}]",
                is_substrules=True, substrules_options=options)
        elif re.fullmatch(r"\[filter_(cmds|commands)(_regex)?\]", phrases[0])!=None:
            self.check_extra_args(phrases, 1)
            reset_outline_foregroundonly()
            command_filter_is_regex=re.fullmatch(r"\[filter_(cmds|commands)_regex\]", phrases[0])!=None

            prev_linenum=self.linenum()
            # read commands
            content=self.handle_block_input(preserve_indents=False, preserve_empty_lines=False, end_phrase=phrases[0].replace('[','[/'), disallow_other_options=False, disable_char_subst=True)
            command_strings=content.splitlines()
            # If regex, check if pattern is valid
            if command_filter_is_regex:
                for cmd in command_strings:
                    prev_linenum+=1
                    check_pattern(cmd, prev_linenum)

            strictness=0
            # parse strictcmdmatch, exactcmdmatch, and other cmdmatch options here
            got_options=copy.copy(self.global_options)
            inline_options={}
            if len(phrases)>1:
                allowed_options=self.block_input_options+(self.command_filter_options if not command_filter_is_regex else ["foregroundonly"])
                got_options=self.parse_options(phrases[1:], merge_global_options=True, allowed_options=allowed_options)
                inline_options=self.parse_options(phrases[1:], merge_global_options=False, allowed_options=allowed_options)
            if got_options.get('strictcmdmatch')==True:
                strictness=1
            if got_options.get('exactcmdmatch')==True:
                strictness=2
            if got_options.get('smartcmdmatch')==True:
                strictness=-1
            if "foregroundonly" in inline_options.keys():
                outline_foregroundonly=self.global_options.get('foregroundonly')==True
                self.global_options['foregroundonly']=inline_options['foregroundonly']
            command_filters=command_strings
            command_filter_strictness=strictness
        elif phrases[0] in ("filter_cmd", "filter_command", "filter_cmd_regex", "filter_command_regex"):
            self.check_enough_args(phrases, 2) 
            reset_outline_foregroundonly()
            command_filter_is_regex=phrases[0] in ("filter_command_regex", "filter_cmd_regex")

            content=_globalvar.splitarray_to_string(phrases[1:])
            content=self.parse_content(content, pure_name=True)
            # If regex, check if pattern is valid
            if command_filter_is_regex: check_pattern(content)

            strictness=0
            if self.global_options.get('strictcmdmatch')==True:
                strictness=1
            if self.global_options.get('exactcmdmatch')==True:
                strictness=2
            if self.global_options.get('smartcmdmatch')==True:
                strictness=-1
            command_filters=[content]
            command_filter_strictness=strictness
        elif phrases[0] in ("unset_filter_command", "unset_filter_cmd"):
            self.check_extra_args(phrases, 1)
            reset_outline_foregroundonly()
            command_filters=None
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1)
            self.handle_end_section("substrules")
            break
        else: self.handle_invalid_phrase(phrases[0])