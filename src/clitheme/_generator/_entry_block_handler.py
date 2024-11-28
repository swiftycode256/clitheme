# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
import re
import copy
import uuid
from typing import Optional, Union, List, Dict, Any
from .. import _globalvar


def handle_entry(obj, entry_name: str, start_phrase: str, end_phrase: str, is_substrules: bool=False, substrules_options: Dict[str, Any]={}):
    # Workaround to circular import issue
    from . import _parser_handlers
    self: _parser_handlers.GeneratorObject=obj
    # substrules_options: {effective_commands: list, is_regex: bool, strictness: int}

    entry_name_substesc=False; entry_name_substvar=False
    names_processed=False # Set to True when no more entry names are being specified

    # For supporting specifying multiple entries at once (0: name, 1: uuid, 2: debug_linenumber)
    entryNames: List[tuple]=[(entry_name, uuid.uuid4(), self.lineindex+1)]
    # For substrules_section: (0: match_content, 1: substitute_content, 2: locale, 3: entry_name_uuid, 4: content_linenumber_str, 5: match_content_linenumber)
    # For entries_section: (0: target_entry, 1: content, 2: debug_linenumber, 3: entry_name_uuid, 4: entry_name_linenumber)
    entries: List[tuple]=[]

    substrules_endmatchhere=False
    substrules_stdout_stderr_option=0
    substrules_foregroundonly=False

    def check_valid_pattern(pattern: str, debug_linenumber: Union[str, int]=self.lineindex+1):
        # check if patterns are valid
        try: re.compile(pattern)
        except: self.handle_error(self.fd.feof("bad-match-pattern-err", "Bad match pattern at line {num} ({error_msg})", num=str(debug_linenumber), error_msg=sys.exc_info()[1]))
    while self.goto_next_line():
        phrases=self.lines_data[self.lineindex].split()
        line_content=self.lines_data[self.lineindex]
        # Support specifying multiple match pattern/entry names in one definition block
        if phrases[0]!=start_phrase and not names_processed:
            names_processed=True # Prevent specifying it after other definition syntax
            # --Process entry names--
            for x in range(len(entryNames)):
                each_entry=entryNames[x]
                name=each_entry[0]
                if not is_substrules:
                    if self.in_subsection!="": name=self.in_subsection+" "+name
                    if self.in_domainapp!="": name=self.in_domainapp+" "+name
                entryNames[x]=(name, each_entry[1], each_entry[2])
                    
        if phrases[0]==start_phrase and not names_processed:
            self.check_enough_args(phrases, 2)
            pattern=_globalvar.extract_content(line_content)
            entryNames.append((pattern, uuid.uuid4(), self.lineindex+1))
        elif phrases[0]=="locale" or phrases[0].startswith("locale:"):
            content: str
            locale: str
            if phrases[0].startswith("locale:"):
                self.check_enough_args(phrases, 2)
                results=re.search(r"locale:(?P<locale>.+)", phrases[0])
                if results==None:
                    self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="locale:<locale>", num=str(self.lineindex+1)))
                else:
                    locale=results.groupdict()['locale']
                content=_globalvar.extract_content(line_content)
            else:
                self.check_enough_args(phrases, 3)
                content=_globalvar.extract_content(line_content, begin_phrase_count=2)
                locale=phrases[1]
            locales=self.parse_content(locale, pure_name=True).split()
            content=self.parse_content(content)
            for this_locale in locales:
                for each_name in entryNames:
                    if is_substrules:
                        entries.append((each_name[0], content, None if this_locale=="default" else this_locale, each_name[1], str(self.lineindex+1), each_name[2]))
                    else:
                        target_entry=copy.copy(each_name[0])
                        if this_locale!="default":
                            target_entry+="__"+this_locale
                        entries.append((target_entry, content, self.lineindex+1, each_name[1], each_name[2]))
        elif phrases[0] in ("locale_block", "[locale]"):
            self.check_enough_args(phrases, 2)
            locales=self.parse_content(_globalvar.splitarray_to_string(phrases[1:]), pure_name=True).split()
            begin_line_number=self.lineindex+1+1
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/locale]" if phrases[0]=="[locale]" else "end_block")
            for this_locale in locales:
                for each_name in entryNames:
                    if is_substrules:
                        entries.append((each_name[0], content, None if this_locale=="default" else this_locale, each_name[1], self.handle_linenumber_range(begin_line_number, self.lineindex+1-1), each_name[2]))
                    else:
                        target_entry=copy.copy(each_name[0])
                        if this_locale!="default":
                            target_entry+="__"+this_locale
                        entries.append((target_entry, content, begin_line_number, each_name[1], each_name[2]))
        elif phrases[0]==end_phrase:
            got_options=self.parse_options(phrases[1:] if len(phrases)>1 else [], merge_global_options=True, \
                    allowed_options=\
                        (self.subst_limiting_options if is_substrules else [])
                        +(self.content_subst_options if is_substrules else ["substvar"]) # don't allow substesc in `[entry]`
                        +(['foregroundonly'] if is_substrules else [])
                    )
            for option in got_options:
                if option=="endmatchhere" and got_options['endmatchhere']==True:
                    substrules_endmatchhere=True
                elif option=="subststdoutonly" and got_options['subststdoutonly']==True:
                    substrules_stdout_stderr_option=1
                elif option=="subststderronly" and got_options['subststderronly']==True:
                    substrules_stdout_stderr_option=2
                elif option=="substesc" and got_options['substesc']==True:
                    entry_name_substesc=True
                elif option=="substvar" and got_options['substvar']==True:
                    entry_name_substvar=True
                elif option=="foregroundonly" and got_options['foregroundonly']==True:
                    substrules_foregroundonly=True
            break
        else: self.handle_invalid_phrase(phrases[0])
    # For silence_warning in subst_variable_content
    encountered_ids=set()
    for x in range(len(entries)):
        entry=entries[x]
        match_pattern=entry[0]
        # substvar MUST come before substesc or "{{ESC}}" in variable content will not be processed
        debug_linenumber=entry[5] if is_substrules else entry[4]
        if entry_name_substvar: 
            match_pattern=self.subst_variable_content(match_pattern, override_check=True, \
                    line_number_debug=debug_linenumber, \
                    # Don't show warnings for the same match_pattern
                    silence_warnings=entry[3] in encountered_ids)
        match_pattern=self.handle_substesc(match_pattern, condition=entry_name_substesc==True, line_number_debug=debug_linenumber)

        if is_substrules: check_valid_pattern(match_pattern, entry[5])
        else:
            # Prevent leading . & prevent /,\ in entry name
            if _globalvar.sanity_check(match_pattern)==False:
                self.handle_error(self.fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=str(entry[4]), sanitycheck_msg=_globalvar.sanity_check_error_message))
        encountered_ids.add(entry[3])
        if is_substrules:
            try: 
                self.db_interface.add_subst_entry(
                    match_pattern=match_pattern, \
                    substitute_pattern=entry[1], \
                    effective_commands=substrules_options['effective_commands'], \
                    effective_locale=entry[2], \
                    is_regex=substrules_options['is_regex'], \
                    command_match_strictness=substrules_options['strictness'], \
                    end_match_here=substrules_endmatchhere, \
                    stdout_stderr_matchoption=substrules_stdout_stderr_option, \
                    foreground_only=substrules_foregroundonly, \
                    line_number_debug=entry[4], \
                    file_id=self.file_id, \
                    unique_id=entry[3])
            except self.db_interface.bad_pattern: self.handle_error(self.fd.feof("bad-subst-pattern-err", "Bad substitute pattern at line {num} ({error_msg})", num=entry[4], error_msg=sys.exc_info()[1]))
        else:
            self.add_entry(self.datapath, match_pattern, entry[1], entry[2])