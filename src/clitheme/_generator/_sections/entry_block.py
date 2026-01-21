# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
import re
import uuid
from typing import List, Dict, Any, Optional
from typing import NamedTuple
from ... import _globalvar
from .. import db_interface

def handle_entry(obj, start_phrase: str, end_phrase: str, is_substrules: bool=False, substrules_options: Dict[str, Any]={}):
    # Workaround to circular import issue
    from .. import _parser_handlers
    self: _parser_handlers.GeneratorObject=obj
    # substrules_options: {effective_commands: list, command_is_regex: bool, is_regex: bool, strictness: int}

    class EntryName(NamedTuple):
        value: str
        is_multiline: bool
        id: uuid.UUID
        line_number: str
    entry_names: List[EntryName]=[]

    class Entry(NamedTuple):
        content: str # /substitute_content
        content_line_number: str
        locale: Optional[str]
    entry_items: List[Entry]=[]

    substrules_stdout_stderr_option=0
    got_options=None

    def check_entry_name(name: str) -> bool:
        if is_substrules: 
            # check if patterns are valid
            try: re.compile(name)
            except:
                self.handle_error(self.fd.feof("bad-match-pattern-err", "Line {num}: Bad match pattern ({error_msg})", num=self.linenum(), error_msg=self.fmt(str(sys.exc_info()[1]))))
                return False
        else:
            if _globalvar.sanity_check(name)==False:
                self.handle_error(self.fd.feof("sanity-check-entry-err", "Line {num}: Entry subsections/names {sanitycheck_msg}", num=self.linenum(), sanitycheck_msg=_globalvar.sanity_check_error_message))
                return False
        return True
    def add_entry(content: str, locales: List[str], line_number: Optional[str]=None):
        for this_locale in locales:
            entry_items.append(Entry(
                content=content,
                content_line_number=line_number if line_number!=None else str(self.linenum()),
                locale=None if this_locale=="default" else this_locale
            ))

    names_processed=False # Set to True when no more entry names are allowed
    start_index=self.lineindex-1 # Process current line
    # Check for options first
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        if phrases[0]==end_phrase:
            got_options=self.parse_options(phrases[1:], merge_global_options=True, \
                    allowed_options=(self.substrules_options if is_substrules else []))
            if got_options.get('subststdoutonly')==True:
                substrules_stdout_stderr_option=1
            if got_options.get('subststderronly')==True:
                substrules_stdout_stderr_option=2
            break
    def opt(name: str) -> bool: 
        assert got_options!=None
        return got_options.get(name)==True
    # Rewind back to start of block
    self.lineindex=start_index
    while self.goto_next_line():
        phrases=self.get_current_line().split()
        line_content=self.get_current_line()
        # Stop allowing more match pattern/entry names after other content
        if phrases[0] not in (start_phrase, start_phrase.replace(']', '>>')):
            names_processed=True

        ## Entry names/Match patterns
        if phrases[0]==start_phrase and not names_processed:
            self.check_enough_args(phrases, 2, check_processed=not is_substrules)
            pattern=_globalvar.extract_content(line_content)
            pattern=self.parse_content(pattern, pure_name=not is_substrules)
            if is_substrules and substrules_options['is_regex']==False: 
                pattern=re.escape(pattern)
            if check_entry_name(pattern):
                entry_names.append(EntryName(
                    value=pattern,
                    is_multiline=False,
                    id=_globalvar.gen_uuid(),
                    line_number=str(self.linenum())
                ))
        elif phrases[0]==start_phrase.replace(']','>>') and not names_processed and is_substrules:
            # e.g. '[subst_regex>>' syntax
            assert re.match(r"^\[.+\]$", start_phrase)!=None, "Start phrase doesn't follow [<name>] format"
            self.check_extra_args(phrases, 1)
            begin_line_number=self.linenum()+1
            pattern_lines=self.handle_block_input_splitlines(
                # e.g. '<<subst_regex]' syntax
                end_phrase=start_phrase.replace('[', '<<'),
                preserve_empty_lines=True,
                preserve_indents=True,
            )
            if substrules_options['is_regex']==False:
                pattern_lines=[re.escape(line) for line in pattern_lines]
            if check_entry_name('\n'.join(pattern_lines)):
                # Match newlines with different types of output newline characters
                newline_sep=[s.decode('utf-8') for s in _globalvar.newlines] \
                            +([r"\x1b\[\d+;\d+H"] if opt("nlmatchcurpos")==True else [])
                line_separator=rf"(?:{'|'.join(newline_sep)})"
                pattern=line_separator.join(pattern_lines)
                entry_names.append(EntryName(
                    value=pattern,
                    is_multiline=True,
                    id=_globalvar.gen_uuid(),
                    line_number=self.handle_linenumber_range(begin_line_number, self.linenum()-1)
                ))
        ## Entry contents/Subst patterns
        elif phrases[0].startswith('locale['):
            locale_match=re.match(r"^locale\[(?P<names>.+?)\]:(?!\S+)", self.get_current_line().strip())
            if locale_match!=None and len(locale_match.group('names').split())>0:
                argc=len(locale_match.group().split())
                self.check_enough_args(phrases, argc+1, disp=locale_match.group(), check_processed=False)
                locales=self.parse_content(locale_match.group('names').strip(), pure_name=2).split()
                if len(locales)==0: # e.g. Empty variable content
                    self.handle_error(self.fd.feof("not-enough-args-err", "Line {num}: Not enough arguments for \"{phrase}\"", phrase="<name> @ locale[<name>]:", num=self.linenum()))
                content=_globalvar.extract_content(self.get_current_line(), begin_phrase_count=argc)
                add_entry(self.parse_content(content), locales) 
            else: 
                self.handle_error(self.fd.feof("phrase-format-err", "Line {num}: Invalid format for \"{phrase}\"", phrase="locale", num=self.linenum()))
        elif phrases[0]=="default:": # Shorthand for "locale[default]:"
            self.check_enough_args(phrases, 2, check_processed=False)
            content=_globalvar.extract_content(self.get_current_line())
            add_entry(self.parse_content(content), ['default'])
        # Old syntax
        elif phrases[0]=="locale" or re.fullmatch(r"locale:(.+)", phrases[0])!=None:
            if phrases[0].startswith("locale:"):
                self.check_enough_args(phrases, 2, check_processed=False)
                results=re.fullmatch(r"locale:(?P<locale>.+)", phrases[0])
                assert results!=None, "Failed to match locale:<name> format"
                locale=results.groupdict()['locale']
                content=_globalvar.extract_content(line_content)
            else:
                self.check_enough_args(phrases, 3, check_processed=False)
                content=_globalvar.extract_content(line_content, begin_phrase_count=2)
                locale=phrases[1]
            locales=self.parse_content(locale, pure_name=2).split()
            if len(locales)==0: # e.g. Empty variable content
                self.handle_error(self.fd.feof("not-enough-args-err", "Line {num}: Not enough arguments for \"{phrase}\"", phrase="<name> @ locale:<name>", num=self.linenum()))
            add_entry(self.parse_content(content), locales)
        ## Content blocks for entry contents/subst patterns
        elif phrases[0] in ("[locale]", "locale_block"):
            self.check_enough_args(phrases, 2)
            locales=self.parse_content(' '.join(phrases[1:]), pure_name=True).split()
            begin_line_number=self.linenum()+1
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True,
                    end_phrase="[/locale]" if phrases[0]=="[locale]" else "end_block",
                    line_separator='\r\n' if is_substrules else '\n'
            )
            add_entry(content, locales, line_number=self.handle_linenumber_range(begin_line_number, self.linenum()-1))
        elif phrases[0]=="[default]": # Shorthand for "[locale] default"
            self.check_extra_args(phrases, 1)
            begin_line_number=self.linenum()+1
            content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True,
                    end_phrase="[/default]",
                    line_separator='\r\n' if is_substrules else '\n'
            )
            add_entry(content, ['default'], line_number=self.handle_linenumber_range(begin_line_number, self.linenum()-1))
        elif phrases[0]==end_phrase:
            assert got_options!=None, "Options should be handled by previous loop"
            break
        else: self.handle_invalid_phrase(phrases[0])
    else: return # Skip processing if entry block is unterminated
    for entry_name in entry_names:
        checked_entries=set() # Don't show multiple errors for same sub pattern within a match pattern
        for entry in entry_items:
            # Displayed line number: (entry name #)>(entry #)[(locale)] (e.g. 64>65[default])
            line_number_debug=\
                f"{entry_name.line_number}>{entry.content_line_number}"+\
                f"[{'default' if entry.locale==None else _globalvar.make_printable(entry.locale)}]"
            if is_substrules:
                try: 
                    db_interface.add_subst_entry(
                        match_pattern=entry_name.value,
                        substitute_pattern=entry.content,
                        is_regex=substrules_options['is_regex'],
                        match_is_multiline=entry_name.is_multiline,
                        effective_commands=substrules_options['effective_commands'],
                        command_match_strictness=substrules_options['strictness'],
                        command_is_regex=substrules_options['command_is_regex'],
                        effective_locale=entry.locale,
                        end_match_here=opt('endmatchhere'),
                        stdout_stderr_matchoption=substrules_stdout_stderr_option,
                        foreground_only=opt('foregroundonly'),
                        line_number_debug=line_number_debug,
                        file_id=self.file_id,
                        unique_id=entry_name.id,
                        warning_handler=self.handle_warning,
                        warning_handler_fd=self.fd
                    )
                except db_interface.bad_pattern:
                    if entry.content_line_number not in checked_entries:
                        self.handle_error(self.fd.feof("bad-subst-pattern-err", "Line {num}: Bad substitute pattern ({error_msg})", num=f"{entry_name.line_number}>{entry.content_line_number}", error_msg=self.fmt(str(sys.exc_info()[1]))))
                        checked_entries.add(entry.content_line_number)
            else:
                target_entry=' '.join(entry_name.value.split()) # Remove extra spaces
                if entry.locale!=None: target_entry+="__"+entry.locale
                if self.in_subsection!="": target_entry=self.in_subsection+" "+target_entry
                if self.in_domainapp!="": target_entry=self.in_domainapp+" "+target_entry
                self.add_entry(self.datapath, target_entry, entry.content, line_number_debug)