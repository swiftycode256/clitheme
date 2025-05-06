# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
substrules_section parser function (internal module)
"""
import os
import copy
from typing import Optional
from .. import _globalvar
from . import _parser_handlers

# spell-checker:ignore infofile splitarray datapath lineindex banphrases cmdmatch minspaces blockinput optline matchoption endphrase filecontent 

def handle_substrules_section(obj: _parser_handlers.GeneratorObject, first_phrase: str):
    obj.handle_begin_section("substrules")
    end_phrase=r"{/substrules_section}"
    command_filters: Optional[list]=None
    command_filter_strictness=0
    # If True, reset foregroundonly option to beforehand during next command filter
    outline_foregroundonly=None
    def reset_outline_foregroundonly():
        """
        Set foregroundonly option to false if foregroundonly option is "inline" and not enabled previously
        """
        nonlocal outline_foregroundonly
        if outline_foregroundonly!=None:
            obj.global_options['foregroundonly']=outline_foregroundonly
            outline_foregroundonly=None
    # initialize the database
    if os.path.exists(obj.path+"/"+_globalvar.db_filename):
        try: obj.db_interface.connect_db(path=obj.path+"/"+_globalvar.db_filename)
        except obj.db_interface.need_db_regenerate:
            from ..exec import _check_regenerate_db
            if not _check_regenerate_db(obj.path): obj.handle_error(obj.fd.reof("db-regenerate-fail-err", "Failed to migrate existing substrules database; try performing the operation without using \"--overlay\""), not_syntax_error=True)
            obj.db_interface.connect_db(path=obj.path+"/"+_globalvar.db_filename)
    else: obj.db_interface.init_db(obj.path+"/"+_globalvar.db_filename)
    obj.db_interface.debug_mode=not obj.silence_warn
    while obj.goto_next_line():
        phrases=obj.lines_data[obj.lineindex].split()
        if phrases[0]=="[filter_commands]":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            reset_outline_foregroundonly()
            content=obj.handle_block_input(preserve_indents=False, preserve_empty_lines=False, end_phrase=r"[/filter_commands]", disallow_other_options=False, disable_substesc=True)
            # read commands
            command_strings=content.splitlines()

            strictness=0
            # parse strictcmdmatch, exactcmdmatch, and other cmdmatch options here
            got_options=copy.copy(obj.global_options)
            inline_options={}
            if len(obj.lines_data[obj.lineindex].split())>1:
                got_options=obj.parse_options(obj.lines_data[obj.lineindex].split()[1:], merge_global_options=True, allowed_options=obj.block_input_options+obj.command_filter_options)
                inline_options=obj.parse_options(obj.lines_data[obj.lineindex].split()[1:], merge_global_options=False, allowed_options=obj.block_input_options+obj.command_filter_options)
            for this_option in got_options:
                if this_option=="strictcmdmatch" and got_options['strictcmdmatch']==True:
                    strictness=1
                elif this_option=="exactcmdmatch" and got_options['exactcmdmatch']==True:
                    strictness=2
                elif this_option=="smartcmdmatch" and got_options['smartcmdmatch']==True:
                    strictness=-1
                elif this_option=="foregroundonly" and "foregroundonly" in inline_options.keys():
                    outline_foregroundonly=obj.global_options.get('foregroundonly')==True
                    obj.global_options['foregroundonly']=inline_options['foregroundonly']
            command_filters=[]
            for cmd in command_strings:
                command_filters.append(cmd.strip())
            command_filter_strictness=strictness
        elif phrases[0]=="filter_command":
            obj.check_enough_args(phrases, 2) 
            reset_outline_foregroundonly()
            content=_globalvar.splitarray_to_string(phrases[1:])
            content=obj.parse_content(content, pure_name=True)
            strictness=0
            for this_option in obj.global_options:
                if this_option=="strictcmdmatch" and obj.global_options['strictcmdmatch']==True:
                    strictness=1
                elif this_option=="exactcmdmatch" and obj.global_options['exactcmdmatch']==True:
                    strictness=2
                elif this_option=="smartcmdmatch" and obj.global_options['smartcmdmatch']==True:
                    strictness=-1
            command_filters=[content]
            command_filter_strictness=strictness
        elif phrases[0]=="unset_filter_command":
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            reset_outline_foregroundonly()
            command_filters=None
        elif phrases[0] in ("[subst_string]", "[substitute_string]", "[subst_regex]", "[substitute_regex]"):
            obj.check_enough_args(phrases, 2)
            options={"effective_commands": copy.copy(command_filters),
                      "is_regex": phrases[0] in ("[subst_regex]", "[substitute_regex]"),
                      "strictness": command_filter_strictness}
            match_pattern=_globalvar.extract_content(obj.lines_data[obj.lineindex])
            obj.handle_entry(match_pattern, start_phrase=phrases[0], end_phrase=phrases[0].replace('[', '[/'), is_substrules=True, substrules_options=options)
        elif obj.handle_setters(): pass
        elif phrases[0]==end_phrase:
            obj.check_extra_args(phrases, 1, use_exact_count=True)
            obj.handle_end_section("substrules")
            break
        else: obj.handle_invalid_phrase(phrases[0])