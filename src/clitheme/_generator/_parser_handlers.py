# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Functions used by various parsers (internal module)
"""

import re
import math
import copy
import uuid
from typing import Optional, Union, List, Dict, Tuple

from ._sections import entry_block
from .. import _globalvar, _version
from . import _data_handlers
# spell-checker:ignore lineindex banphrases minspaces blockinput optline datapath matchoption

class GeneratorObject(_data_handlers.DataHandlers):

    ## Defined option groups
    lead_indent_options=["leadtabindents", "leadspaces"]
    content_subst_options=["substvar", "linebounds"]
    char_subst_options=["substesc", "substchar"]
    subst_options=content_subst_options+char_subst_options
    command_filter_options=["strictcmdmatch", "exactcmdmatch", "smartcmdmatch", "normalcmdmatch"]+["foregroundonly"]
    subst_limiting_options=["subststdoutonly", "subststderronly", "substallstreams"]+["endmatchhere"]
    
    # options used in handle_block_input
    block_input_options=lead_indent_options+subst_options

    # value options: options requiring an integer value
    value_options=lead_indent_options
    # on/off options (use no<...> to disable)
    bool_options=subst_options+["endmatchhere", "foregroundonly"]
    # only one of these options can be set to true at the same time (specific to groups)
    switch_options=[command_filter_options[:4]]
    # Disable these options for now (BETA)
    # switch_options+=[subst_limiting_options[:3]]
    substvar_banphrases=['{', '}', '[', ']', '(', ')']

    def __init__(self, file_content: str, custom_infofile_name: str, filename: str, path: str, silence_warn: bool):
        # data to keep track of
        self.warnings: Dict[str, bool]={}
        self.section_parsing=False
        self.parsed_sections=[]
        self.lines_data=file_content.splitlines()
        self.lineindex=-1 # counter extra +1 operation at beginning
        self.global_options={}
        self.really_really_global_options={} # options defined outside any sections
        self.global_variables={}
        self.really_really_global_variables={} # variables defined outside any sections
        # For in_domainapp and in_subsection in {entries}
        self.in_domainapp=""
        self.in_subsection=""

        self.custom_infofile_name=custom_infofile_name
        self.filename=filename
        self.file_content=file_content
        self.file_id=uuid.uuid4()
        _data_handlers.DataHandlers.__init__(self, path, silence_warn)
    def is_ignore_line(self) -> bool:
        return self.get_current_line().strip()=="" or self.get_current_line().strip().startswith('#')
    def goto_next_line(self) -> bool:
        while self.lineindex<len(self.lines_data)-1:
            self.lineindex+=1
            # stop at non-empty or non-comment line
            if not self.is_ignore_line(): return True
        else: return False # End of file
    def linenum(self) -> int:
        return self.lineindex+1
    def get_current_line(self) -> str:
        return self.lines_data[self.lineindex]
    def handle_invalid_phrase(self, name: str):
        self.handle_error(self.fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=self.fmt(name), num=self.linenum()))
    def handle_unterminated_section(self, name: str):
        self.handle_error(self.fd.feof("unterminated-section-err", "Unterminated {name} section at end of file", name=name))
    def check_enough_args(self, phrases: List[str], count: int, disp: Optional[str]=None, check_processed: bool=True):
        if check_processed:
            # Check processed phrases after the first
            processed=self.parse_content(' '.join(phrases[1:]), pure_name=True)
            # If rest of content only contains spaces
            success=len(processed.split())+1>=count
        else:
            # Check unprocessed phrases
            success=len(phrases)>=count

        if not success:
            if disp==None: disp=phrases[0]
            self.handle_error(self.fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase=self.fmt(disp), num=self.linenum()))
        
    def check_extra_args(self, phrases: List[str], count: int, disp: Optional[str]=None, check_processed: bool=True):
        if check_processed:
            # Check processed phrases after the first
            processed=self.parse_content(' '.join(phrases[1:]), pure_name=True)
            # If rest of content only contains spaces
            success=len(processed.split())+1<=count
        else:
            # Check unprocessed phrases
            success=len(phrases)<=count

        if not success:
            if disp==None: disp=phrases[0]
            self.handle_error(self.fd.feof("extra-arguments-err", "Extra arguments after \"{phrase}\" on line {num}", num=self.linenum(), phrase=self.fmt(disp)))
    def check_version(self, version_str: str):
        # allow_bugfix is disabled to allow interoperability with other release variants
        allow_bugfix: bool=False # Whether to allow specifying bugfix releases in version info
        match_result=re.match(rf"^(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<bugfix>\d+)){{,{int(allow_bugfix)}}}(-beta(?P<beta_release>\d+))?$", version_str)
        def invalid_version(): self.handle_error(self.fd.feof("invalid-version-err", "Invalid version information \"{ver}\" on line {num}", ver=self.fmt(version_str), num=self.linenum()))
        if match_result==None: invalid_version()
        elif int(match_result.groupdict()['major'])<2: invalid_version()
        else:
            version_ok= int(match_result.groupdict()['major'])<=_version.major \
                        and int(match_result.groupdict()['minor'])<=_version.minor \
                        and (int(match_result.groupdict()['bugfix'])<=_version.release if match_result.groupdict().get("bugfix")!=None else True)
            if match_result.groupdict().get("beta_release")!=None:
                if _version.beta_release!=None:
                    version_ok=version_ok and int(match_result.groupdict()['beta_release'])<=_version.beta_release
            else:
                # If did not specify beta, current version cannot be beta
                version_ok=version_ok and _version.beta_release==None

            if not version_ok:
                self.handle_error(self.fd.feof("unsupported-version-err", "Current version of CLItheme ({cur_ver}) does not support this file (requires {req_ver} or higher)", 
                        cur_ver=_globalvar.clitheme_version+ \
                            # For "dev" versions: output corresponding beta milestone
                            (f" [beta{_version.beta_release}]" if _version.beta_release!=None and not "beta" in _globalvar.clitheme_version else ""),
                        req_ver=self.fmt(version_str)), not_syntax_error=True)
    def parse_options(self, options_data: List[str], merge_global_options: int, allowed_options: Optional[List[str]]=None, ban_options: Optional[List[str]]=None) -> Dict[str, Union[int,bool]]:
        # merge_global_options: 0 - Don't merge; 1 - Merge self.global_options; 2 - Merge self.really_really_global_options
        assert not (allowed_options!=None and ban_options!=None), "Cannot specify allowed and banned options at the same time"

        final_options={}
        if merge_global_options!=0: final_options=copy.copy(self.global_options if merge_global_options==1 else self.really_really_global_options)
        if len(options_data)==0: return final_options # return either empty data or pre-existing global options
        options_data=self.parse_content(' '.join(options_data), pure_name=True).split()
        for each_option in options_data:
            option_name=re.sub(r"^(no)?(?P<name>.+?)(:.+)?$", r"\g<name>", each_option)
            option_name_preserve_no=re.sub(r"^(?P<name>.+?)(:.+)?$", r"\g<name>", each_option)
            if option_name_preserve_no in self.value_options: # must not begin with "no"
                # get value
                results=re.search(r"^(?P<name>.+?):(?P<value>.+)$", each_option)
                value: int
                if results==None: # no value specified
                    self.handle_error(self.fd.feof("option-without-value-err", "No value specified for option \"{phrase}\" on line {num}", num=self.linenum(), phrase=self.fmt(option_name)))
                else: 
                    try: value=int(results.groupdict()['value'])
                    except ValueError: self.handle_error(self.fd.feof("option-value-not-int-err", "The value specified for option \"{phrase}\" is not an integer on line {num}", num=self.linenum(), phrase=self.fmt(option_name)))
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
                                self.handle_error(self.fd.feof("option-conflict-err", "The option \"{option1}\" can't be set at the same time with \"{option2}\" on line {num}", num=self.linenum(), option1=self.fmt(option_name_preserve_no), option2=self.fmt(opt)))
                        # set all other options to false
                        for opt in option_group: final_options[opt]=False
                        # set the option
                        final_options[option_name_preserve_no]=True
                        break
                else: # executed when no break occurs
                    self.handle_error(self.fd.feof("unknown-option-err", "Unknown option \"{phrase}\" on line {num}", num=self.linenum(), phrase=self.fmt(option_name_preserve_no)))
            if (allowed_options!=None and option_name not in allowed_options) or\
               (ban_options!=None and option_name in ban_options):
                self.handle_error(self.fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=self.linenum(), phrase=self.fmt(option_name)))
        return final_options 
    def handle_set_global_options(self, options_data: List[str], really_really_global: bool=False):
        # set options globally
        if really_really_global: 
            self.really_really_global_options=self.parse_options(options_data, merge_global_options=2)
        self.global_options=self.parse_options(options_data, merge_global_options=1) 
        specified_options=self.parse_options(options_data, merge_global_options=False)
        # if manually disabled, show substvar warning again next time
        for option in self.subst_options:
            if self.global_options.get(option)!=True \
                and option in specified_options:
                self.warnings[option]=True
    def handle_setup_global_options(self):
        prev_options=copy.copy(self.global_options)
        # reset global_options to contents of really_really_global_options
        self.global_options=copy.copy(self.really_really_global_options)
        # if manually disabled, show warnings again next time
        for option in self.subst_options:
            if self.global_options.get(option)!=True and prev_options.get(option)==True:
                self.warnings[option]=True
        self.global_variables=copy.copy(self.really_really_global_variables)
    def handle_subst(self, content: str, line_number_debug: Optional[str]=None, silence_warnings: Union[bool, Tuple[bool, bool, bool]]=False, subst_var: Optional[bool]=None, subst_esc: Optional[bool]=None, subst_chars: Optional[bool]=None) -> str:
        # silence_warnings: (substvar, substesc, substchar)
        substvar_pattern=r"{{([^\s]+?)??}}"
        substchar_pattern=r"{{\[([^\s]+?)??\]}}"

        subst_var=self.global_options.get("substvar")==True if subst_var==None else subst_var
        subst_chars=self.global_options.get("substchar")==True if subst_chars==None else subst_chars
        subst_esc=self.global_options.get("substesc")==True if subst_esc==None else subst_esc

        if type(silence_warnings)==bool: silence_warn=(silence_warnings,)*3
        else: silence_warn=silence_warnings
        # Handle substvar warning
        if not silence_warn[0] and subst_var!=True and self.warnings.get('substvar')!=False:
            for match in re.finditer(substvar_pattern, content):
                if self.global_variables.get(match.group(1))!=None:
                    self.handle_warning(self.fd.feof("set-substvar-warn", "Line {num}: attempted to reference a defined variable, but \"substvar\" option is not enabled", num=line_number_debug if line_number_debug!=None else self.linenum()))
                    # self.warnings['substvar']=False
                    break
        # Handle substesc warning
        if not silence_warn[1] and subst_esc!=True and self.warnings.get('substesc')!=False:
            if "{{ESC}}" in content:
                self.handle_warning(self.fd.feof("set-substesc-warn", "Line {num}: attempted to use \"{{{{ESC}}}}\", but \"substesc\" option is not enabled", num=line_number_debug if line_number_debug!=None else self.linenum()))
                # self.warnings['substesc']=False
        # Handle substchar warning
        if not silence_warn[2] and subst_chars!=True and self.warnings.get('substchar')!=False:
            if re.match(substchar_pattern, content)!=None:
                self.handle_warning(self.fd.feof("set-substchar-warn", "Line {num}: attempted to use character substitution, but \"substchar\" option is not enabled", num=line_number_debug if line_number_debug!=None else self.linenum()))
                # self.warnings['substchar']=False
                
        # get all variables used in content
        new_content=content
        if subst_var:
            offset=0
            encountered_variables=set()
            for match in re.finditer(substvar_pattern, content):
                var_name=match.group(1)
                if var_name==None or var_name.strip()=='': continue
                if var_name=="ESC": continue # skip {{ESC}}; leave it for substesc
                if re.match(r"^\[.+\]$", var_name)!=None: continue # skip substchar format

                var_content=None
                try: 
                    var_content=self.global_variables[var_name]
                except KeyError: 
                    if not silence_warnings and var_name not in encountered_variables: self.handle_warning(self.fd.feof("unknown-variable-warn", "Line {num}: unknown variable \"{name}\", not performing substitution", \
                        num=line_number_debug if line_number_debug!=None else self.linenum(), name=self.fmt(var_name)))
                if var_content!=None:
                    new_content=new_content[:match.start()+offset]+var_content+new_content[match.end()+offset:]
                    offset+=len(var_content)-(match.end()-match.start())
                encountered_variables.add(var_name) # Prevent repeated warnings
        # substesc
        if subst_esc:
            new_content=new_content.replace("{{ESC}}", "\x1b")
        # substchar
        content=new_content
        if subst_chars:
            offset=0
            for match in re.finditer(substchar_pattern, content):
                pattern=match.group(1)
                if pattern==None or pattern.strip()=='': continue
                
                char_content=None
                # Match x,u,U formats
                m=re.match(r"^(x.{2}|u.{4}|U.{8})$", pattern)
                if m!=None:
                    # Convert to character
                    try: char_content=chr(int(m.string[1:], base=16))
                    except ValueError: 
                        if not silence_warnings: self.handle_warning(self.fd.feof("invalid-charcode-warn", "Line {num}: invalid character code \"{name}\", not performing substitution", num=line_number_debug if line_number_debug!=None else self.linenum(), name=self.fmt(m.string[1:])))
                else:
                    if not silence_warnings: self.handle_warning(self.fd.feof("invalid-substchar-format-warn", "Line {num}: invalid substchar format \"{name}\", not performing substitution", num=line_number_debug if line_number_debug!=None else self.linenum(), name=self.fmt(pattern)))
                if char_content!=None:
                    new_content=new_content[:match.start()+offset]+char_content+new_content[match.end()+offset:]
                    offset+=len(char_content)-(match.end()-match.start())
        return new_content
    def handle_linebounds(self, content: str, condition: Optional[bool]=None, preserve_indents: bool=True, debug_linenumber: Optional[int]=None) -> str:
        # Skip if not starts with |
        if not content.strip().startswith('|'): return content

        match=re.match(r"^\|(.*)\|$", content.strip())
        condition=self.global_options.get('linebounds')==True if condition==None else condition
        if condition==False:
            # Linebounds warning
            if match!=None and self.warnings.get('linebounds')!=False:
                self.handle_warning(self.fd.feof("set-linebounds-warn", "Line {num}: Attempted to use line boundaries, but \"linebounds\" option is not enabled", num=str(self.linenum() if debug_linenumber==None else debug_linenumber)))
                # self.warnings['linebounds']=False
            return content
        # Match pattern |...|
        if match!=None:
            content=match.group(1)
            return content if preserve_indents else content.strip()
        else:
            self.handle_error(self.fd.feof("linebounds-format-err", "Invalid line boundary format at line {num}", num=str(self.linenum() if debug_linenumber==None else debug_linenumber)))
    def handle_set_variable(self, var_name: str, var_content: str, really_really_global: bool=False):
        # sanity check var_name
        def bad_var(): self.handle_error(self.fd.feof("bad-var-name-err", "Line {num}: \"{name}\" is not a valid variable name", name=self.fmt(var_name), num=self.linenum()))
        if var_name=='ESC': bad_var()
        for char in self.substvar_banphrases:
            if char in var_name: bad_var()

        # Parse content without substesc (subst variable content)
        var_content=self.parse_content(var_content, pure_name=True, preserve_indents=True)
        # set variable
        if really_really_global: self.really_really_global_variables[var_name]=var_content
        self.global_variables[var_name]=var_content
    def handle_begin_section(self, section_name: str):
        if section_name in self.parsed_sections: 
            self.handle_error(self.fd.feof("repeated-section-err", "Repeated {section} section at line {num}", num=self.linenum(), section=section_name))
        self.section_parsing=True
        self.handle_setup_global_options()
    def handle_end_section(self, section_name: str):
        self.parsed_sections.append(section_name)
        self.section_parsing=False
        self.handle_setup_global_options()
    def handle_linenumber_range(self, begin: int, end: int) -> str:
        if begin==end: return str(end)
        else: return f"{begin}-{end}"
    def parse_content(self, content: str, pure_name: bool=False, preserve_indents: Optional[bool]=None) -> str:
        target_content=self.handle_subst(content,
            subst_chars=pure_name==False and self.global_options.get("substchar")==True,
            subst_esc=pure_name==False and self.global_options.get("substesc")==True,
            # Don't show substchar/substesc warnings if not using char subst
            silence_warnings=(False, pure_name, pure_name)
        )
        if preserve_indents==None: preserve_indents=not pure_name
        target_content=self.handle_linebounds(target_content, preserve_indents=preserve_indents)
        return target_content if preserve_indents else target_content.strip()
    def handle_setters(self, really_really_global: bool=False) -> bool:
        # Handle set_options and setvar
        phrases=self.get_current_line().split()
        setvar_match_old=re.fullmatch(r"setvar:(?P<name>.+)", phrases[0])
        if phrases[0].startswith('setvar['):
            setvar_match=re.match(r"^setvar\[(?P<names>.+?)\]:(?!\S+)", self.get_current_line().strip())
            if setvar_match!=None and len(setvar_match.group('names').split())>0:
                argc=len(setvar_match.group().split())
                self.check_enough_args(phrases, argc+1, disp=setvar_match.group(), check_processed=False)
                var_content=_globalvar.extract_content(self.get_current_line(), begin_phrase_count=argc)
                for var_name in setvar_match.group('names').split():
                    self.handle_set_variable(var_name, var_content, really_really_global)
            else:
                self.handle_error(self.fd.feof("phrase-format-err", "Invalid format for \"{phrase}\" on line {num}", phrase="setvar", num=self.linenum()))
        elif setvar_match_old!=None:
            self.check_enough_args(phrases, 2, check_processed=False)
            var_name=setvar_match_old.group('name')
            var_content=_globalvar.extract_content(self.get_current_line(), begin_phrase_count=1)
            self.handle_set_variable(var_name, var_content, really_really_global)
        elif phrases[0] in ("(set_options)", "set_options"):
            self.check_enough_args(phrases, 2)
            self.handle_set_global_options(' '.join(phrases[1:]).split(), really_really_global)
        elif phrases[0]=="(enable_subst)":
            self.check_extra_args(phrases, 1)
            self.handle_set_global_options(self.subst_options, really_really_global)
        elif phrases[0]=="(disable_subst)":
            self.check_extra_args(phrases, 1)
            self.handle_set_global_options([f"no{opt}" for opt in self.subst_options], really_really_global)
        else: return False
        return True
    
    ## sub-block processing functions

    def handle_block_input(self, preserve_indents: bool, preserve_empty_lines: bool, end_phrase: str, disallow_other_options: bool=True, disable_char_subst: bool=False, disable_content_subst: bool=False) -> str:
        minspaces=math.inf
        blockinput_data=""
        begin_line_number=self.linenum()+1
        while self.lineindex<len(self.lines_data)-1:
            self.lineindex+=1
            # read line
            line=self.get_current_line().rstrip()
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
                    line=leading_whitespace+re.sub(r"^\\([\\]*)"+re.escape(end_phrase), r"\g<1>"+end_phrase, line.strip())
                    # update minspaces
                    minspaces=min(minspaces, len(leading_whitespace))
            else: # don't preserve whitespaces
                line=re.sub(r"^\\([\\]*)"+re.escape(end_phrase), r"\g<1>"+end_phrase, line.strip())
            # write to data
            blockinput_data+="\n"+line
        else: # File terminated without reaching end phrase
            self.handle_error(self.fd.feof("unterminated-content-block-err", "Unterminated content block at line {num}", num=begin_line_number-1))
        # remove the extra leading newline
        blockinput_data=re.sub(r"\A\n", "", blockinput_data)
        # remove all whitespaces except common minspaces
        if preserve_indents:
            pattern=r"(?P<optline>\n|^)[ ]{"+str(minspaces)+"}"
            blockinput_data=re.sub(pattern,r"\g<optline>", blockinput_data, flags=re.MULTILINE)

        ## Parse options
        got_options=copy.copy(self.global_options)
        def opt(name: str): return got_options.get(name)

        if len(self.get_current_line().split())>1:
            # Allowed/banned options
            ban_options=None; allowed_options=None
            if not disallow_other_options:
                ban_options=[]
                if not preserve_indents: ban_options+=self.lead_indent_options
                if disable_char_subst: ban_options+=self.char_subst_options
                if disable_content_subst: ban_options+=self.content_subst_options
            else:
                allowed_options=[]
                if preserve_indents: allowed_options+=self.lead_indent_options
                if not disable_char_subst: allowed_options+=self.char_subst_options
                if not disable_content_subst: allowed_options+=self.content_subst_options
            got_options=self.parse_options(self.get_current_line().split()[1:],
                merge_global_options=True,
                allowed_options=allowed_options, ban_options=ban_options)
        # Process lead indent options
        if preserve_indents and opt("leadtabindents")!=None:
            blockinput_data=re.sub(r"^", r"\t"*int(got_options['leadtabindents']), blockinput_data, flags=re.MULTILINE)
        if preserve_indents and opt("leadspaces")!=None:
            blockinput_data=re.sub(r"^", " "*int(got_options['leadspaces']), blockinput_data, flags=re.MULTILINE)
        # Process subst options
        debug_linenumber=self.handle_linenumber_range(begin_line_number, self.linenum()-1)
        blockinput_data=self.handle_subst(blockinput_data, 
                subst_var=opt("substvar")==True, 
                subst_esc=opt("substesc")==True and not disable_char_subst,
                subst_chars=opt("substchar")==True and not disable_char_subst,
                silence_warnings=(False, disable_char_subst, disable_char_subst),
                line_number_debug=debug_linenumber)
        # Process linebounds
        blockinput_lines=[]
        offset=0
        for line in blockinput_data.splitlines():
            ws_match=re.match(r"^(?P<spc>\s*)", line)
            assert ws_match!=None
            leading_whitespace=ws_match.groupdict()['spc']
            blockinput_lines.append(leading_whitespace+self.handle_linebounds(line.strip(), condition=opt("linebounds")==True, preserve_indents=preserve_indents, debug_linenumber=begin_line_number+offset))
            offset+=1
        blockinput_data="\n".join(blockinput_lines)
        return blockinput_data
    handle_entry=entry_block.handle_entry