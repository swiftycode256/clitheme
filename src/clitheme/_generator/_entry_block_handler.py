# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
import re
import copy
import uuid
from typing import Union, List, Dict, Any, Optional
from typing import NamedTuple
from .. import _globalvar
from . import db_interface

# spell-checker:ignore matchoption datapath lineindex

def handle_entry(obj, start_phrase: str, end_phrase: str, is_substrules: bool=False, substrules_options: Dict[str, Any]={}):
    # Workaround to circular import issue
    from . import _parser_handlers
    self: _parser_handlers.GeneratorObject=obj
    # substrules_options: {effective_commands: list, is_regex: bool, strictness: int}

    names_processed=False # Set to True when no more entry names are being specified

    # For supporting specifying multiple entries at once (0: name, 1: uuid, 2: debug_linenumber)
    class EntryName(NamedTuple):
        value: str
        is_multiline: bool
        id: uuid.UUID
        line_number: str
    entry_names: List[EntryName]=[]
    # For substrules_section: (0: match_content, 1: substitute_content, 2: locale, 3: entry_name_uuid, 4: content_linenumber_str, 5: match_content_linenumber)
    # For entries_section: (0: target_entry, 1: content, 2: debug_linenumber, 3: entry_name_uuid, 4: entry_name_linenumber)
    class Entry(NamedTuple):
        entry_name: EntryName # /match_content =entry_name.value
        content: str # /substitute_content
        content_line_number: str
        locale: Optional[str]
    entry_items: List[Entry]=[]

    substrules_stdout_stderr_option=0
    got_options=None
    def opt(name: str) -> bool: 
        assert got_options!=None
        return got_options.get(name)==True

    def check_valid_pattern(pattern: str, debug_linenumber: Union[str, int]):
        # check if patterns are valid
        try: 
            if len(pattern)==0:
                raise ValueError("empty pattern")
            re.compile(pattern)
        except: self.handle_error(self.fd.feof("bad-match-pattern-err", "Bad match pattern at line {num} ({error_msg})", num=str(debug_linenumber), error_msg=sys.exc_info()[1]))

    self.lineindex-=1 # Process current line
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        line_content=self.get_current_line()
        # Support specifying multiple match pattern/entry names in one definition block
        if phrases[0]!=start_phrase and not names_processed:
            names_processed=True # Prevent specifying it after other definition syntax
            # --Process entry names--
            for x in range(len(entry_names)):
                each_entry=entry_names[x]
                name=each_entry[0]
                if not is_substrules:
                    if self.in_subsection!="": name=self.in_subsection+" "+name
                    if self.in_domainapp!="": name=self.in_domainapp+" "+name
                entry_names[x]=EntryName(value=name, is_multiline=each_entry.is_multiline, id=each_entry.id, line_number=each_entry.line_number)
                    
        if phrases[0]==start_phrase and not names_processed:
            self.check_enough_args(phrases, 2, check_processed=False)
            pattern=_globalvar.extract_content(line_content)
            entry_names.append(EntryName(
                value=pattern,
                is_multiline=False,
                id=uuid.uuid4(),
                line_number=str(self.linenum())
            ))
        elif phrases[0]==start_phrase.replace(']','>>') and is_substrules:
            # e.g. '[subst_regex>>' syntax
            assert re.match(r"^\[.+\]$", phrases[0])!=None, "Start phrase doesn't follow [<name>] format"
            self.check_extra_args(phrases, 1)
            begin_line_number=self.linenum()+1
            # Only allow indent options in this block input
            pattern=self.handle_block_input(
                # e.g. '<<subst_regex]' syntax
                end_phrase=start_phrase.replace('[', '<<'),
                preserve_empty_lines=True,
                preserve_indents=True,
                disable_char_subst=True, disable_content_subst=True
            )
            entry_names.append(EntryName(
                value=pattern,
                is_multiline=True,
                id=uuid.uuid4(),
                line_number=self.handle_linenumber_range(begin_line_number, self.linenum()-1)
            ))
        elif phrases[0]=="locale" or phrases[0].startswith("locale:"):
            content: str
            locale: str
            if phrases[0].startswith("locale:"):
                self.check_enough_args(phrases, 2, check_processed=False)
                results=re.search(r"locale:(?P<locale>.+)", phrases[0])
                if results==None:
                    self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="locale:<name>", num=self.linenum()))
                else:
                    locale=results.groupdict()['locale']
                content=_globalvar.extract_content(line_content)
            else:
                self.check_enough_args(phrases, 3, check_processed=False)
                content=_globalvar.extract_content(line_content, begin_phrase_count=2)
                locale=phrases[1]
            locales=self.parse_content(locale, pure_name=True).split()
            if len(locales)==0:
                self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="locale:<name>", num=self.linenum()))
            content=self.parse_content(content)
            for this_locale in locales:
                for each_name in entry_names:
                    entry_items.append(Entry(
                        entry_name=each_name,
                        content=content,
                        content_line_number=str(self.linenum()),
                        locale=None if this_locale=="default" else this_locale
                    ))
        elif phrases[0] in ("locale_block", "[locale]"):
            self.check_enough_args(phrases, 2)
            locales=self.parse_content(_globalvar.splitarray_to_string(phrases[1:]), pure_name=True).split()
            begin_line_number=self.linenum()+1
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/locale]" if phrases[0]=="[locale]" else "end_block")
            for this_locale in locales:
                for each_name in entry_names:
                    entry_items.append(Entry(
                        entry_name=each_name,
                        content=content,
                        content_line_number=self.handle_linenumber_range(begin_line_number, self.linenum()-1),
                        locale=None if this_locale=="default" else this_locale
                    ))
        elif phrases[0]==end_phrase:
            got_options=self.parse_options(phrases[1:], merge_global_options=True, \
                    allowed_options=\
                        (self.subst_limiting_options if is_substrules else [])
                        +(self.subst_options if is_substrules else self.content_subst_options) # don't allow char subst in `[entry]`
                        +(['foregroundonly'] if is_substrules else [])
                    )
            if got_options.get('subststdoutonly')==True:
                substrules_stdout_stderr_option=1
            if got_options.get('subststderronly')==True:
                substrules_stdout_stderr_option=2
            break
        else: self.handle_invalid_phrase(phrases[0])
    # For silence_warning in subst_variable_content
    encountered_ids=set()
    for entry in entry_items:
        match_pattern=entry.entry_name.value
        # substvar MUST come before substesc or "{{ESC}}" in variable content will not be processed
        match_pattern=self.handle_subst(match_pattern, 
                subst_var=opt('substvar'),
                subst_esc=opt('substesc') and is_substrules,
                subst_chars=opt('substchar') and is_substrules, 
                line_number_debug=entry.entry_name.line_number, 
                # Don't show warnings for the same match_pattern
                silence_warnings=True if entry.entry_name.id in encountered_ids else (False, not is_substrules, not is_substrules))
        match_pattern=self.handle_linebounds(match_pattern, condition=opt('linebounds'), preserve_indents=is_substrules)
        encountered_ids.add(entry.entry_name.id)

        if is_substrules: check_valid_pattern(match_pattern, entry.content_line_number)
        else:
            # Prevent leading . & prevent /,\ in entry name
            if _globalvar.sanity_check(match_pattern)==False:
                self.handle_error(self.fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=entry.entry_name.line_number, sanitycheck_msg=_globalvar.sanity_check_error_message))
        if is_substrules:
            try: 
                db_interface.add_subst_entry(
                    match_pattern=match_pattern,
                    substitute_pattern=entry.content,
                    is_regex=substrules_options['is_regex'],
                    match_is_multiline=entry.entry_name.is_multiline,
                    effective_commands=substrules_options['effective_commands'],
                    command_match_strictness=substrules_options['strictness'],
                    command_is_regex=substrules_options['command_is_regex'],
                    effective_locale=entry.locale,
                    end_match_here=opt('endmatchhere'),
                    stdout_stderr_matchoption=substrules_stdout_stderr_option,
                    foreground_only=opt('foregroundonly'),
                    line_number_debug=entry.content_line_number,
                    file_id=self.file_id,
                    unique_id=entry.entry_name.id)
            except db_interface.bad_pattern: self.handle_error(self.fd.feof("bad-subst-pattern-err", "Bad substitute pattern at line {num} ({error_msg})", num=entry.content_line_number, error_msg=sys.exc_info()[1]))
        else:
            target_entry=copy.copy(match_pattern).strip()
            if entry.locale!=None:
                target_entry+="__"+entry.locale
            self.add_entry(self.datapath, target_entry, entry.content, entry.content_line_number)