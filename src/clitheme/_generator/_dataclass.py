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
from typing import Optional
from .. import _globalvar
from . import _handlers
# spell-checker:ignore lineindex banphrases cmdmatch minspaces blockinput optline datapath matchoption

class GeneratorObject(_handlers.DataHandlers):

    ## Defined option groups
    lead_indent_options=["leadtabindents", "leadspaces"]
    content_subst_options=["substesc","substvar"]
    command_filter_options=["strictcmdmatch", "exactcmdmatch", "smartcmdmatch", "normalcmdmatch"]
    subst_limiting_options=["subststdoutonly", "subststderronly", "substall"]
    
    # options used in handle_block_input
    block_input_options=lead_indent_options+content_subst_options

    # value options: options requiring an integer value
    value_options=lead_indent_options
    # on/off options (use no<...> to disable)
    bool_options=content_subst_options+["endmatchhere"]
    # only one of these options can be set to true at the same time (specific to groups)
    switch_options=[command_filter_options]
    # Disable these options for now (BETA)
    # switch_options+=[subst_limiting_options]

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

        self.custom_infofile_name=custom_infofile_name
        self.filename=filename
        self.file_content=file_content
        _handlers.DataHandlers.__init__(self, path, silence_warn)
        from . import db_interface
        self.db_interface=db_interface
    def is_ignore_line(self) -> bool:
        return self.lines_data[self.lineindex].strip()=="" or self.lines_data[self.lineindex].strip().startswith('#')
    def check_enough_args(self, phrases: list[str], count: int):
        if len(phrases)<count:
            self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase=phrases[0], num=str(self.lineindex+1)))
    def check_extra_args(self, phrases: list[str], count: int, use_exact_count: bool):
        not_pass: bool
        if use_exact_count: not_pass=len(phrases)!=count
        else: not_pass=len(phrases)>count
        if not_pass:
            self.handle_error(self.fd.feof("extra-arguments-err", "Extra arguments after \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=phrases[0]))
    def parse_options(self, options_data: list[str], merge_global_options: int, allowed_options: Optional[list]=None) -> dict:
        final_options={}
        if merge_global_options!=0: final_options=copy.copy(self.global_options if merge_global_options==1 else self.really_really_global_options)
        if len(options_data)==0: return final_options # return either empty data or pre-existing global options
        for each_option in options_data:
            option_name=re.sub(r"^(no)*(?P<name>.+?)(:.+)*$", r"\g<name>", each_option)
            option_name_preserve_no=re.sub(r"^(?P<name>.+?)(:.+)*$", r"\g<name>", each_option)
            if allowed_options!=None and option_name not in allowed_options:
                self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=option_name))
            if option_name_preserve_no in self.value_options: # must not begin with "no"
                # get value
                results=re.search(r"^(?P<name>.+?):(?P<value>.+)+$", each_option)
                value: int
                if results==None: # no value specified
                    self.handle_error(self.fd.feof("option-without-value-err", "No value specified for option \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=option_name))
                else: 
                    try: value=int(results.groupdict()['value'])
                    except ValueError: self.handle_error(self.fd.feof("option-value-not-int-err", "The value specified for option \"{phrase}\" is not an integer on line {num}", num=str(self.lineindex+1), phrase=option_name))
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
                                self.handle_error(self.fd.feof("option-conflict-err", "The option \"{option1}\" can't be set at the same time with \"{option2}\" on line {num}", num=str(self.lineindex+1), option1=option_name_preserve_no, option2=opt))
                        # set all other options to false
                        for opt in option_group: final_options[opt]=False
                        # set the option
                        final_options[option_name_preserve_no]=True
                        break
                else: # executed when no break occurs
                    self.handle_error(self.fd.feof("unknown-option-err", "Unknown option \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=option_name_preserve_no))
        return final_options 
    def handle_set_global_options(self, options_data: list[str], really_really_global: bool=False):
        # set options globally
        if really_really_global: 
            self.really_really_global_options=self.parse_options(options_data, merge_global_options=2)
        else:
            self.global_options=self.parse_options(options_data, merge_global_options=1) 
    def handle_setup_global_options(self):
        # reset global_options to contents of really_really_global_options
        self.global_options=copy.copy(self.really_really_global_options)
        self.global_variables=copy.copy(self.really_really_global_variables)
    def subst_variable_content(self, content: str, override_check: bool=False) -> str:
        if not override_check and (not "substvar" in self.global_options or self.global_options["substvar"]==False): return content
        # get all variables used in content
        new_content=copy.copy(content)
        variables=re.findall(r"{{(.+?)}}", content)
        if len(variables)>0:
            for var_name in variables:
                if var_name=="ESC": continue # skip {{ESC}}; leave it for substesc
                var_content: str
                try: 
                    var_content=self.global_variables[var_name]
                except KeyError: 
                    self.handle_warning(self.fd.feof("unknown-variable-warn", "Line {num}: unknown variable \"{name}\", not performing substitution", num=str(self.lineindex+1), name=var_name))
                    continue
                new_content=new_content.replace(r"{{"+var_name+r"}}", var_content)
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
        def bad_var(): self.handle_error(self.fd.feof("bad-var-name-err", "Line {num}: \"{name}\" is not a valid variable name", name=var_name, num=str(self.lineindex+1)))
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
    def handle_singleline_content(self, content: str) -> str:
        target_content=copy.copy(content)
        target_content=self.subst_variable_content(target_content)
        if "substesc" in self.global_options.keys() and self.global_options['substesc']==True:
            target_content=self.handle_substesc(target_content)
        return target_content
    
    ## sub-block processing functions

    def handle_block_input(self, preserve_indents: bool, preserve_empty_lines: bool, end_phrase: str="end_block", disallow_cmdmatch_options: bool=True, disable_substesc: bool=False) -> str:
        minspaces=math.inf
        blockinput_data=""
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
            def is_specified_in_block() -> bool: return option in specified_options.keys() and specified_options[option]==True
            if option=="leadtabindents": 
                if not preserve_indents and is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=option))
                # insert tabs at start of each line
                if preserve_indents: blockinput_data=re.sub(r"^", r"\t"*int(got_options['leadtabindents']), blockinput_data, flags=re.MULTILINE)
            elif option=="leadspaces":
                if not preserve_indents and is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=option))
                # insert spaces at start of each line
                if preserve_indents: blockinput_data=re.sub(r"^", " "*int(got_options['leadspaces']), blockinput_data, flags=re.MULTILINE)
            elif option=="substesc":
                if disable_substesc and is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=option))
                # substitute {{ESC}} with escape literal
                if got_options['substesc']==True and not disable_substesc: blockinput_data=self.handle_substesc(blockinput_data)
            elif option=="substvar":
                if got_options['substvar']==True: blockinput_data=self.subst_variable_content(blockinput_data, True)
            elif disallow_cmdmatch_options:
                self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=option))
        return blockinput_data
    def handle_entry(self, entry_name: str, end_phrase: str, is_substrules: bool=False, substrules_options: dict={}):
        # substrules_options: effective_commands: list[str], is_regex: bool, strictness: int
        unique_id=uuid.uuid4()
        substrules_entries=[] # (match_content, substitute_content, locale)
        substrules_entries_linenumber=[]
        substrules_endmatchhere=False
        substrules_stdout_stderr_option=0
        if is_substrules:
            # check if patterns are valid
            try: re.compile(entry_name)
            except: self.handle_error(self.fd.feof("bad-match-pattern-err", "Bad match pattern at line {num} ({error_msg})", num=str(self.lineindex+1), error_msg=sys.exc_info()[1]))
        while self.lineindex<len(self.lines_data)-1:
            self.lineindex+=1
            if self.is_ignore_line(): continue
            phrases=self.lines_data[self.lineindex].split()
            if phrases[0]=="locale" or phrases[0].startswith("locale:"):
                content: str
                locale: str
                if phrases[0].startswith("locale:"):
                    self.check_enough_args(phrases, 2)
                    results=re.search(r"locale:(?P<locale>.+)", phrases[0])
                    if results==None:
                        self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="locale:<locale>", num=str(self.lineindex+1)))
                    else:
                        locale=results.groupdict()['locale']
                    content=_globalvar.extract_content(self.lines_data[self.lineindex])
                else:
                    self.check_enough_args(phrases, 3)
                    content=_globalvar.extract_content(self.lines_data[self.lineindex], begin_phrase_count=2)
                    locale=phrases[1]
                target_entry=copy.copy(entry_name)
                content=self.handle_singleline_content(content) # handle substesc and substvar
                if locale!="default":
                    target_entry+="__"+locale
                if not is_substrules: self.add_entry(self.datapath, target_entry, content, self.lineindex+1)
                else: substrules_entries.append((entry_name, content, None if locale=="default" else locale)); substrules_entries_linenumber.append(self.lineindex+1)
            elif phrases[0]=="locale_block" or phrases[0]=="[locale]":
                self.check_enough_args(phrases, 2)
                locales=phrases[1:]
                content=self.handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/locale]" if phrases[0]=="[locale]" else "end_block")
                for this_locale in locales:
                    suffix=""
                    if this_locale!="default":
                        suffix="__"+this_locale
                    if not is_substrules: self.add_entry(self.datapath, entry_name+suffix, content, self.lineindex+1)
                    else: substrules_entries.append((entry_name, content, None if this_locale=="default" else this_locale)); substrules_entries_linenumber.append(self.lineindex+1)
            elif phrases[0]==end_phrase:
                if not is_substrules: self.check_extra_args(phrases, 1, use_exact_count=True)
                got_options=self.parse_options(phrases[1:] if len(phrases)>1 else [], merge_global_options=True, allowed_options=self.subst_limiting_options+["endmatchhere"])
                for option in got_options:
                    if option=="endmatchhere" and got_options['endmatchhere']==True:
                        substrules_endmatchhere=True
                    elif option=="subststdoutonly" and got_options['subststdoutonly']==True:
                        substrules_stdout_stderr_option=1
                    elif option=="subststderronly" and got_options['subststderronly']==True:
                        substrules_stdout_stderr_option=2
                break
            else: self.handle_error(self.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(self.lineindex+1)))
        if is_substrules:
            for x in range(len(substrules_entries)):
                entry=substrules_entries[x]
                try: self.db_interface.add_subst_entry(match_pattern=entry[0], substitute_pattern=entry[1], effective_commands=substrules_options['effective_commands'], effective_locale=entry[2], is_regex=substrules_options['is_regex'], command_match_strictness=substrules_options['strictness'], end_match_here=substrules_endmatchhere, stdout_stderr_matchoption=substrules_stdout_stderr_option, line_number_debug=substrules_entries_linenumber[x], unique_id=unique_id)
                except self.db_interface.bad_pattern: self.handle_error(self.fd.feof("bad-subst-pattern-err", "Bad substitute pattern at line {num} ({error_msg})", num=str(substrules_entries_linenumber[x]), error_msg=sys.exc_info()[1]))