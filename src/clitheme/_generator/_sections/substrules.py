# Copyright © 2023-2026 swiftycode

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
from ... import _globalvar
from .. import _parser_handlers, db_interface

# spell-checker:ignore itute

def handle_substrules_section(self: _parser_handlers.GeneratorObject, end_phrase: str):
    self.handle_begin_section("substrules")
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
        except re.error: self.handle_error(self.fd.feof("bad-cmd-filter-pattern-err", "Line {num}: Bad command filter pattern ({error_msg})", num=str(linenum if linenum!=None else self.linenum()), error_msg=self.fmt(str(sys.exc_info()[1]))))

    if os.path.exists(self.path+"/"+_globalvar.db_filename):
        # Connect to existing database
        try: db_interface.connect_db(path=self.path+"/"+_globalvar.db_filename)
        except:
            self.handle_syntax_error(self.fd.reof("db-compat-err", "The current substrules database version is incompatible; please run \"clitheme repair-theme\" and try again"), no_prefix=True)
    else:
        # Initialize the database
        db_interface.init_db(self.path+"/"+_globalvar.db_filename)
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
            got_options=self.global_options
            inline_options={}
            end_options=self.get_current_line().split()[1:]
            if len(end_options)>0:
                allowed_options=self.block_input_options+(self.command_filter_options if not command_filter_is_regex else ["foregroundonly"])
                got_options=self.parse_options(end_options, merge_global_options=True, allowed_options=allowed_options)
                inline_options=self.parse_options(end_options, merge_global_options=False, allowed_options=allowed_options)
            if got_options.get('strictcmdmatch')==True: strictness=1
            if got_options.get('exactcmdmatch')==True: strictness=2
            if got_options.get('smartcmdmatch')==True: strictness=-1
            if "foregroundonly" in inline_options.keys():
                outline_foregroundonly=self.global_options.get('foregroundonly')==True
                self.global_options['foregroundonly']=inline_options['foregroundonly']
            command_filters=command_strings
            command_filter_strictness=strictness
        elif re.fullmatch(r"(\<)?filter_(cmd|command)(_regex)?(?(1)\>|)", phrases[0])!=None:
            self.check_enough_args(phrases, 2) 
            reset_outline_foregroundonly()
            command_filter_is_regex=re.fullmatch(r"(\<)?filter_(cmd|command)_regex(?(1)\>|)", phrases[0])!=None

            content=' '.join(phrases[1:])
            content, got_options, inline_options=self.parse_content_with_options(content, pure_name=True,
                        extra_options=(self.command_filter_options if not command_filter_is_regex else ["foregroundonly"]))
            # If regex, check if pattern is valid
            if command_filter_is_regex: check_pattern(content)

            strictness=0
            if got_options.get('strictcmdmatch')==True: strictness=1
            if got_options.get('exactcmdmatch')==True: strictness=2
            if got_options.get('smartcmdmatch')==True: strictness=-1
            if "foregroundonly" in inline_options.keys():
                outline_foregroundonly=self.global_options.get('foregroundonly')==True
                self.global_options['foregroundonly']=inline_options['foregroundonly']
            command_filters=[content]
            command_filter_strictness=strictness
        elif re.fullmatch(r"(\<)?unset_filter_(cmd|command)(?(1)\>|)", phrases[0])!=None:
            self.check_extra_args(phrases, 1)
            reset_outline_foregroundonly()
            command_filters=None
        elif self.handle_setters(): pass
        elif phrases[0]==end_phrase:
            self.check_extra_args(phrases, 1)
            self.handle_end_section("substrules")
            db_interface.connection.commit()
            db_interface.connection.close()
            break
        else: self.handle_invalid_phrase(phrases[0])
    else: self.handle_unterminated_section("substrules")