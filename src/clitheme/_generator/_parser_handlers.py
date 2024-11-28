# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Functions used by various parsers (internal module)
"""

import sys
import re
import math
import copy
import uuid
from typing import Optional, Union, List, Dict
from .. import _globalvar, _version
from . import _data_handlers, _entry_block_handler
# spell-checker:ignore lineindex banphrases cmdmatch minspaces blockinput optline datapath matchoption

class GeneratorObject(_data_handlers.DataHandlers):

    ## Defined option groups
    lead_indent_options=["leadtabindents", "leadspaces"]
    content_subst_options=["substesc","substvar"]
    command_filter_options=["strictcmdmatch", "exactcmdmatch", "smartcmdmatch", "normalcmdmatch"]+["foregroundonly"]
    subst_limiting_options=["subststdoutonly", "subststderronly", "substallstreams"]+["endmatchhere"]
    
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
    substvar_banphrases=['{', '}', '[', ']', '(', ')']

    def __init__(self, file_content: str, custom_infofile_name: str, filename: str, path: str, silence_warn: bool):
        # data to keep track of
        self.substvar_warning=True
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
        self.file_id=uuid.uuid4()
        _data_handlers.DataHandlers.__init__(self, path, silence_warn)
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
    def check_enough_args(self, phrases: List[str], count: int):
        if len(phrases)<count:
            self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase=self.fmt(phrases[0]), num=str(self.lineindex+1)))
    def check_extra_args(self, phrases: List[str], count: int, use_exact_count: bool):
        not_pass: bool
        if use_exact_count: not_pass=len(phrases)!=count
        else: not_pass=len(phrases)>count
        if not_pass:
            self.handle_error(self.fd.feof("extra-arguments-err", "Extra arguments after \"{phrase}\" on line {num}", num=str(self.lineindex+1), phrase=self.fmt(phrases[0])))
    def check_version(self, version_str: str):
        match_result=re.match(r"^(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<bugfix>\d+))?(-beta(?P<beta_release>\d+))?$", version_str)
        def invalid_version(): self.handle_error(self.fd.feof("invalid-version-err", "Invalid version information \"{ver}\" on line {num}", ver=self.fmt(version_str), num=str(self.lineindex+1)))
        if match_result==None: invalid_version()
        elif int(match_result.groupdict()['major'])<2: invalid_version()
        else:
            version_ok= int(match_result.groupdict()['major'])<=_version.major \
                        and int(match_result.groupdict()['minor'])<=_version.minor \
                        and (int(match_result.groupdict()['bugfix']) if match_result.groupdict().get("bugfix")!=None else -1)<=_version.release
            if match_result.groupdict().get("beta_release")!=None and _version.beta_release!=None:
                version_ok=version_ok and int(match_result.groupdict()['beta_release'])<=_version.beta_release

            if not version_ok:
                self.handle_error(self.fd.feof("unsupported-version-err", "Current version of clitheme ({cur_ver}) does not support this file (requires {req_ver} or higher)", 
                        cur_ver=_version.__version__+ \
                            (f" [beta{_version.beta_release}]" if _version.beta_release!=None and not "beta" in _version.__version__ else ""),
                        req_ver=self.fmt(version_str)), not_syntax_error=True)
    def handle_invalid_phrase(self, name: str):
        self.handle_error(self.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=self.fmt(name), num=str(self.lineindex+1)))
    def parse_options(self, options_data: List[str], merge_global_options: int, allowed_options: Optional[list]=None) -> Dict[str, Union[int,bool]]:
        # merge_global_options: 0 - Don't merge; 1 - Merge self.global_options; 2 - Merge self.really_really_global_options
        final_options={}
        if merge_global_options!=0: final_options=copy.copy(self.global_options if merge_global_options==1 else self.really_really_global_options)
        if len(options_data)==0: return final_options # return either empty data or pre-existing global options
        options_data=self.parse_content(_globalvar.splitarray_to_string(options_data), pure_name=True).split()
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
    def handle_set_global_options(self, options_data: List[str], really_really_global: bool=False):
        # set options globally
        if really_really_global: 
            self.really_really_global_options=self.parse_options(options_data, merge_global_options=2)
        self.global_options=self.parse_options(options_data, merge_global_options=1) 
        # if manually disabled, show substvar warning again next time
        if self.global_options.get("substvar")!=True \
            and "substvar" in self.parse_options(options_data, merge_global_options=False):
            self.substvar_warning=True
    def handle_setup_global_options(self):
        # reset global_options to contents of really_really_global_options
        self.global_options=copy.copy(self.really_really_global_options)
        # if manually disabled, show substvar warning again next time
        if self.global_options.get("substvar")!=True: self.substvar_warning=True
        self.global_variables=copy.copy(self.really_really_global_variables)
    def subst_variable_content(self, content: str, override_check: bool=False, line_number_debug: Optional[str]=None, silence_warnings: bool=False) -> str:
        pattern=r"{{([^\s]+?)??}}"
        if not override_check and self.global_options.get("substvar")!=True:
            # Handle substvar warning
            if self.substvar_warning:
                for match in re.finditer(pattern, content):
                    if self.global_variables.get(match.group(1))!=None:
                        self.handle_warning(self.fd.feof("set-substvar-warn", "Line {num}: Attempted to reference a defined variable, but \"substvar\" option is not enabled", num=line_number_debug if line_number_debug!=None else str(self.lineindex+1)))
                        self.substvar_warning=False
                        break
            return content
        # get all variables used in content
        new_content=copy.copy(content)
        encountered_variables=set()
        offset=0
        for match in re.finditer(pattern, content):
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
        for char in self.substvar_banphrases:
            if char in var_name: bad_var()

        var_content=_globalvar.extract_content(line_content)
        # Parse content without substesc (subst variable content)
        var_content=self.parse_content(var_content, pure_name=True)
        # set variable
        if really_really_global: self.really_really_global_variables[var_name]=var_content
        self.global_variables[var_name]=var_content
    def handle_begin_section(self, section_name: str):
        if section_name in self.parsed_sections: 
            self.handle_error(self.fd.feof("repeated-section-err", "Repeated {section} section at line {num}", num=str(self.lineindex+1), section=section_name))
        self.section_parsing=True
        self.handle_setup_global_options()
    def handle_end_section(self, section_name: str):
        self.parsed_sections.append(section_name)
        self.section_parsing=False
        self.handle_setup_global_options()
    def handle_substesc(self, content: str) -> str:
        return content.replace("{{ESC}}", "\x1b")
    def handle_linenumber_range(self, begin: int, end: int) -> str:
        if begin==end: return str(end)
        else: return f"{begin}-{end}"
    def parse_content(self, content: str, pure_name: bool=False) -> str:
        target_content=copy.copy(content)
        target_content=self.subst_variable_content(target_content)
        if pure_name==False and self.global_options.get("substesc")==True:
            target_content=self.handle_substesc(target_content)
        return target_content
    def handle_setters(self, really_really_global: bool=False) -> bool:
        # Handle set_options and setvar
        phrases=self.lines_data[self.lineindex].split()
        if phrases[0]=="set_options":
            self.check_enough_args(phrases, 2)
            self.handle_set_global_options(_globalvar.splitarray_to_string(phrases[1:]).split(), really_really_global)
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
            elif option=="substesc" and not "substvar" in got_options:
                # Only handle substesc independently if substvar is not specified
                check_whether_explicitly_specified(pass_condition=not disable_substesc)
                # substitute {{ESC}} with escape literal
                if got_options['substesc']==True and not disable_substesc: blockinput_data=self.handle_substesc(blockinput_data)
            elif option=="substvar":
                if got_options['substvar']==True: blockinput_data=self.subst_variable_content(blockinput_data, override_check=True, line_number_debug=self.handle_linenumber_range(begin_line_number, self.lineindex+1-1))
                # If substvar, substesc must be handled after that, or "{{ESC}}" in variable content will be ignored
                if got_options.get('substesc')==True and not disable_substesc: blockinput_data=self.handle_substesc(blockinput_data)
            elif disallow_cmdmatch_options:
                if is_specified_in_block(): self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(self.lineindex+1), phrase=self.fmt(option)))
        if "substvar" not in specified_options:
            # Let the function show the substvar warning
            self.subst_variable_content(blockinput_data, override_check=False, line_number_debug=self.handle_linenumber_range(begin_line_number, self.lineindex+1-1))
        return blockinput_data
    handle_entry=_entry_block_handler.handle_entry