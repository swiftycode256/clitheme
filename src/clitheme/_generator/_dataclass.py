# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Class object for sharing data between section parsers (internal module)
"""

import sys
import re
import math
import copy
import uuid
from typing import Optional, Union
from .. import _globalvar
from . import _handlers
# spell-checker:ignore lineindex banphrases cmdmatch minspaces blockinput optline datapath matchoption

class GeneratorObject(_handlers.DataHandlers):

    ## Defined option groups
    lead_indent_options=["leadtabindents", "leadspaces"]
    content_subst_options=["substesc","substvar"]
    command_filter_options=["strictcmdmatch", "exactcmdmatch", "smartcmdmatch", "normalcmdmatch"]+["foregroundonly"]
    subst_limiting_options=["subststdoutonly", "subststderronly", "substall"]+["endmatchhere"]
    
    # options used in handle_block_input
    block_input_options=lead_indent_options+content_subst_options

    # value options: options requiring an integer value
    value_options=lead_indent_options
    # on/off options (use no<...> to disable)
    bool_options=content_subst_options+["endmatchhere", "foregroundonly"]
    # only one of these options can be set to true at the same time (specific to groups)
    switch_options=[command_filter_options[:4]]
    # Disable these options for now (BETA)
    # switch_options+=[subst_limiting_options[:3]]

    def __init__(self, file_content: str, custom_infofile_name: str, filename: str, path: str, silence_warn: bool):
        # data to keep track of
        self.section_parsing=False
        self.parsed_sections=[]
        self.lines_data=file_content.splitlines()
        self.lineindex=-1 # counter extra +1 operation at beginning
        self.global_options={}
        self.really_really_global_options={} # options defined outside any sections
        self.global_variables={}
        self.really_really_global_variables={} # variables defined outside any sections
        # For in_domainapp and in_subsection in {entries_section}
        self.in_domainapp=""
        self.in_subsection=""

        self.custom_infofile_name=custom_infofile_name
        self.filename=filename
        self.file_content=file_content
        _handlers.DataHandlers.__init__(self, path, silence_warn)
        from . import db_interface
        self.db_interface=db_interface
    def is_ignore_line(self) -> bool:
        return self.lines_data[self.lineindex].strip()=="" or self.lines_data[self.lineindex].strip().startswith('#')
    def goto_next_line(self) -> bool:
        while self.lineindex<len(self.lines_data)-1:
            self.lineindex+=1
            # stop at non-empty or non-comment line
            if not self.is_ignore_line(): return True
        else: return False # End of file
    def check_enough_args(self, phrases: list, count: int):
        if len(phrases)<count:
            self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase=self.fmt(phrases[0]), num=str(self.lineindex+1)))
    def check_extra_args(self, phrases: list, count: int, use_exact_count: bool):
        not_pass: bool
        if use_exact_count: not_pass=len(phrases)!=count
        else: not_pass=len(phrases)>count
        if not_pass:
            self.handle_error(self.fd.feof("extra-arguments-err", "Extra arguments after \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=self.fmt(phrases[0])))
    def handle_invalid_phrase(self, name: str):
        self.handle_error(self.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=self.fmt(name), num=str(self.lineindex+1)))
    def parse_options(self, options_data: list, merge_global_options: int, allowed_options: Optional[list]=None) -> dict:
        # merge_global_options: 0 - Don't merge; 1 - Merge self.global_options; 2 - Merge self.really_really_global_options
        final_options={}
        if merge_global_options!=0: final_options=copy.copy(self.global_options if merge_global_options==1 else self.really_really_global_options)
        if len(options_data)==0: return final_options # return either empty data or pre-existing global options
        for each_option in options_data:
            option_name=re.sub(r"^(no)?(?P<name>.+?)(:.+)?$", r"\g<name>", each_option)
            option_name_preserve_no=re.sub(r"^(?P<name>.+?)(:.+)?$", r"\g<name>", each_option)
            if option_name_preserve_no in self.value_options: # must not begin with "no"
                # get value
                results=re.search(r"^(?P<name>.+?):(?P<value>.+)$", each_option)
                value: int
                if results==None: # no value specified
                    self.handle_error(self.fd.feof("option-without-value-err", "No value specified for option \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=self.fmt(option_name)))
                else: 
                    try: value=int(results.groupdict()['value'])
                    except ValueError: self.handle_error(self.fd.feof("option-value-not-int-err", "The value specified for option \"{phrase}\" is not an integer on line {num}", num=str(self.lineindex+1), phrase=self.fmt(option_name)))
                # set option
                final_options[option_name]=value
            elif option_name in self.bool_options:
                # if starts with no, set to false; else, set to true
                final_options[option_name]=not option_name_preserve_no.startswith("no")
            else:
                for option_group in self.switch_options:
                    if option_name_preserve_no in option_group:
                        for opt in options_data:
                            if opt!=option_name_preserve_no and opt in option_group:
                                self.handle_error(self.fd.feof("option-conflict-err", "The option \"{option1}\" can't be set at the same time with \"{option2}\" on line {num}", num=str(self.lineindex+1), option1=self.fmt(option_name_preserve_no), option2=self.fmt(opt)))
                        # set all other options to false
                        for opt in option_group: final_options[opt]=False
                        # set the option
                        final_options[option_name_preserve_no]=True
                        break
                else: # executed when no break occurs
                    self.handle_error(self.fd.feof("unknown-option-err", "Unknown option \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=self.fmt(option_name_preserve_no)))
            if allowed_options!=None and option_name not in allowed_options:
                self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=self.fmt(option_name)))
        return final_options 
    def handle_set_global_options(self, options_data: list, really_really_global: bool=False):
        # set options globally
        if really_really_global: 
            self.really_really_global_options=self.parse_options(options_data, merge_global_options=2)
        else:
            self.global_options=self.parse_options(options_data, merge_global_options=1) 
    def handle_setup_global_options(self):
        # reset global_options to contents of really_really_global_options
        self.global_options=copy.copy(self.really_really_global_options)
        self.global_variables=copy.copy(self.really_really_global_variables)
    def subst_variable_content(self, content: str, override_check: bool=False, line_number_debug: Optional[str]=None, silence_warnings: bool=False) -> str:
        if not override_check and (not "substvar" in self.global_options or self.global_options["substvar"]==False): return content
        # get all variables used in content
        new_content=copy.copy(content)
        encountered_variables=set()
        offset=0
        for match in re.finditer(r"{{([^\s]+?)??}}", content):
            var_name=match.group(1)
            if var_name==None or var_name.strip()=='': continue
            if var_name=="ESC": continue # skip {{ESC}}; leave it for substesc
            var_content: str
            try: 
                var_content=self.global_variables[var_name]
            except KeyError: 
                if not silence_warnings and var_name not in encountered_variables: self.handle_warning(self.fd.feof("unknown-variable-warn", "Line {num}: unknown variable \"{name}\", not performing substitution", \
                    num=line_number_debug if line_number_debug!=None else str(self.lineindex+1), name=self.fmt(var_name)))
            else:
                new_content=new_content[:match.start()+offset]+var_content+new_content[match.end()+offset:]
                offset+=len(var_content)-(match.end()-match.start())
            encountered_variables.add(var_name) # Prevent repeated warnings
        return new_content
    def handle_set_variable(self, line_content: str, really_really_global: bool=False):
        if not line_content.split()[0].startswith("setvar:"): return
        # match variable name
        self.check_enough_args(line_content.split(), 2)
        results=re.search(r"setvar:(?P<name>.+)", line_content.split()[0])
        var_name: str
        if results==None:
            self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="setvar:<variable>", num=str(self.lineindex+1)))
        else: var_name=results.groupdict()['name']
        # sanity check var_name
        def bad_var(): self.handle_error(self.fd.feof("bad-var-name-err", "Line {num}: \"{name}\" is not a valid variable name", name=self.fmt(var_name), num=str(self.lineindex+1)))
        if var_name=='ESC': bad_var()
        banphrases=['{', '}', '[', ']', '(', ')']
        for char in banphrases:
            if char in var_name: bad_var()

        var_content=_globalvar.extract_content(line_content)
        # subst variable references
        check_list=self.really_really_global_options if really_really_global else self.global_options
        if "substvar" in check_list and check_list["substvar"]==True: 
            var_content=self.subst_variable_content(var_content, override_check=True)
        # set variable
        if really_really_global: self.really_really_global_variables[var_name]=var_content
        else: self.global_variables[var_name]=var_content
    def handle_begin_section(self, section_name: str):
        if section_name in self.parsed_sections: 
            self.handle_error(self.fd.feof("repeated-section-err", "Repeated {section} section at line {num}", num=str(self.lineindex+1), section=section_name))
        self.section_parsing=True
        self.handle_setup_global_options()
    def handle_end_section(self, section_name: str):
        self.parsed_sections.append(section_name)
        self.section_parsing=False
    def handle_substesc(self, content: str) -> str:
        return content.replace("{{ESC}}", "\x1b")
    def handle_linenumber_range(self, begin: int, end: int) -> str:
        if begin==end: return str(end)
        else: return f"{begin}-{end}"
    def handle_singleline_content(self, content: str) -> str:
        target_content=copy.copy(content)
        target_content=self.subst_variable_content(target_content)
        if "substesc" in self.global_options.keys() and self.global_options['substesc']==True:
            target_content=self.handle_substesc(target_content)
        return target_content
    def handle_setters(self, really_really_global: bool=False) -> bool:
        # Handle set_options and setvar
        phrases=self.lines_data[self.lineindex].split()
        if phrases[0]=="set_options":
            self.check_enough_args(phrases, 2)
            self.handle_set_global_options(self.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split(), really_really_global)
        elif phrases[0].startswith("setvar:"): 
            self.check_enough_args(phrases, 2)
            self.handle_set_variable(self.lines_data[self.lineindex], really_really_global)
        else: return False
        return True
    
    ## sub-block processing functions

    def handle_block_input(self, preserve_indents: bool, preserve_empty_lines: bool, end_phrase: str="end_block", disallow_cmdmatch_options: bool=True, disable_substesc: bool=False) -> str:
        minspaces=math.inf
        blockinput_data=""
        begin_line_number=self.lineindex+1+1
        while self.lineindex<len(self.lines_data)-1:
            self.lineindex+=1
            # read line
            line=self.lines_data[self.lineindex].rstrip()
            if line.strip()=="": # empty line
                if preserve_empty_lines: blockinput_data+="\n"
                continue
            if line.split()[0]==end_phrase: break
            # if preserve_indents, update minspaces
            if preserve_indents:
                ws_match=re.search(r"^\s+", line) # match leading whitespaces
                if ws_match==None: minspaces=0
                else:
                    # substitute \t with 8 spaces
                    leading_whitespace=ws_match.group()
                    leading_whitespace=re.sub(r"\t", " "*8, leading_whitespace)
                    # update line content
                    # replace \end_block with end_block
                    line=leading_whitespace+re.sub(r"^\\([\\]*)"+end_phrase, r"\g<1>"+end_phrase, line.strip())
                    # update minspaces
                    minspaces=min(minspaces, len(leading_whitespace))
            else: # don't preserve whitespaces
                line=re.sub(r"^\\([\\]*)"+end_phrase, r"\g<1>"+end_phrase, line.strip())
            # write to data
            blockinput_data+="\n"+line
        # remove the extra leading newline
        blockinput_data=re.sub(r"\A\n", "", blockinput_data)
        # remove all whitespaces except common minspaces (if preserve_indents)
        if preserve_indents:
            pattern=r"(?P<optline>\n|^)[ ]{"+str(minspaces)+"}"
            blockinput_data=re.sub(pattern,r"\g<optline>", blockinput_data, flags=re.MULTILINE)
        # parse leadtabindents leadspaces, and substesc options
        got_options=copy.copy(self.global_options)
        specified_options={}
        if len(self.lines_data[self.lineindex].split())>1:
            got_options=self.parse_options(self.lines_data[self.lineindex].split()[1:], merge_global_options=True)
            specified_options=self.parse_options(self.lines_data[self.lineindex].split()[1:], merge_global_options=False)
        for option in got_options.keys():
            def is_specified_in_block() -> bool: return option in specified_options.keys()
            def check_whether_explicitly_specified(pass_condition: bool):
                if not pass_condition and is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=self.fmt(option)))
            if option=="leadtabindents": 
                check_whether_explicitly_specified(pass_condition=preserve_indents)
                # insert tabs at start of each line
                if preserve_indents: blockinput_data=re.sub(r"^", r"\t"*int(got_options['leadtabindents']), blockinput_data, flags=re.MULTILINE)
            elif option=="leadspaces":
                check_whether_explicitly_specified(pass_condition=preserve_indents)
                # insert spaces at start of each line
                if preserve_indents: blockinput_data=re.sub(r"^", " "*int(got_options['leadspaces']), blockinput_data, flags=re.MULTILINE)
            elif option=="substesc":
                check_whether_explicitly_specified(pass_condition=not disable_substesc)
                # substitute {{ESC}} with escape literal
                if got_options['substesc']==True and not disable_substesc: blockinput_data=self.handle_substesc(blockinput_data)
            elif option=="substvar":
                if got_options['substvar']==True: blockinput_data=self.subst_variable_content(blockinput_data, True, line_number_debug=self.handle_linenumber_range(begin_line_number, self.lineindex+1-1))
            elif disallow_cmdmatch_options:
                if is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=self.fmt(option)))
        return blockinput_data
    def handle_entry(self, entry_name: str, start_phrase: str, end_phrase: str, is_substrules: bool=False, substrules_options: dict={}):
        # substrules_options: {effective_commands: list, is_regex: bool, strictness: int, foreground_only: bool}

        entry_name_substesc=False; entry_name_substvar=False
        names_processed=False # Set to True when no more entry names are being specified

        # For supporting specifying multiple entries at once (0: name, 1: uuid, 2: debug_linenumber)
        entryNames: list=[(entry_name, uuid.uuid4(), self.lineindex+1)]
        # For substrules_section: (0: match_content, 1: substitute_content, 2: locale, 3: entry_name_uuid, 4: content_linenumber_str, 5: match_content_linenumber)
        # For entries_section: (0: target_entry, 1: content, 2: debug_linenumber, 3: entry_name_uuid, 4: entry_name_linenumber)
        entries: list=[]

        substrules_endmatchhere=False
        substrules_stdout_stderr_option=0

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
                content=self.handle_singleline_content(content)
                for each_name in entryNames:
                    if is_substrules:
                        entries.append((each_name[0], content, None if locale=="default" else locale, each_name[1], str(self.lineindex+1), each_name[2]))
                    else:
                        target_entry=copy.copy(each_name[0])
                        if locale!="default":
                            target_entry+="__"+locale
                        entries.append((target_entry, content, self.lineindex+1, each_name[1], each_name[2]))
            elif phrases[0]=="locale_block" or phrases[0]=="[locale]":
                self.check_enough_args(phrases, 2)
                locales=self.subst_variable_content(_globalvar.splitarray_to_string(phrases[1:])).split()
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
                            (self.subst_limiting_options if is_substrules else []) \
                            +(self.content_subst_options if is_substrules else ["substvar"]) # don't allow substesc in `[entry]`
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
                break
            else: self.handle_invalid_phrase(phrases[0])
        # For silence_warning in subst_variable_content
        encountered_ids=set()
        for x in range(len(entries)):
            entry=entries[x]
            match_pattern=entry[0]
            # substvar MUST come before substesc or "{{ESC}}" in variable content will not be processed
            if entry_name_substvar: 
                match_pattern=self.subst_variable_content(match_pattern, override_check=True, \
                        line_number_debug=entry[5] if is_substrules else entry[4], \
                        # Don't show warnings for the same match_pattern
                        silence_warnings=entry[3] in encountered_ids)
            if entry_name_substesc: match_pattern=self.handle_substesc(match_pattern)

            if is_substrules: check_valid_pattern(match_pattern, entry[5])
            else:
                # Prevent leading . & prevent /,\ in entry name
                if _globalvar.sanity_check(match_pattern)==False:
                    self.handle_error(self.fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=str(entry[5]), sanitycheck_msg=_globalvar.sanity_check_error_message))
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
                        foreground_only=substrules_options['foreground_only'], \
                        line_number_debug=entry[4], \
                        unique_id=entry[3])
                except self.db_interface.bad_pattern: self.handle_error(self.fd.feof("bad-subst-pattern-err", "Bad substitute pattern at line {num} ({error_msg})", num=entry[4], error_msg=sys.exc_info()[1]))
            else:
                self.add_entry(self.datapath, match_pattern, entry[1], entry[2])