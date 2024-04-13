"""
Generator function used in applying themes (should not be invoked directly)
"""
import os
import string
import random
import re
import math
import copy
try:
    from .. import _globalvar
    from .. import frontend
    from .. import _version
    from .. import _get_resource
except ImportError: # for test program
    import _globalvar
    import frontend
    import _version
    import _get_resource

fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")

path=""
silence_warn=False

def handle_error(message):
    raise SyntaxError(fd.feof("error-str", "Syntax error: {msg}", msg=message))
def handle_warning(message):
    if not silence_warn: print(fd.feof("warning-str", "Warning: {msg}", msg=message))
def recursive_mkdir(path, entry_name, line_number_debug): # recursively generate directories (excluding file itself)
    current_path=path
    current_entry="" # for error output
    for x in entry_name.split()[:-1]:
        current_entry+=x+" "
        current_path+="/"+x
        if os.path.isfile(current_path): # conflict with entry file
            handle_error(fd.feof("subsection-conflict-err", "Line {num}: cannot create subsection \"{name}\" because an entry with the same name already exists", \
                num=str(line_number_debug), name=current_entry))
        elif os.path.isdir(str(current_path))==False: # directory does not exist
           os.mkdir(current_path) 
def add_entry(path, entry_name, entry_content, line_number_debug): # add entry to where it belongs (assuming recursive_mkdir already completed)
    target_path=path
    for x in entry_name.split():
        target_path+="/"+x
    if os.path.isdir(target_path):
        handle_error(fd.feof("entry-conflict-err", "Line {num}: cannot create entry \"{name}\" because a subsection with the same name already exists", \
            num=str(line_number_debug), name=entry_name))
    elif os.path.isfile(target_path):
        handle_warning(fd.feof("repeated-entry-warn", "Line {num}: repeated entry \"{name}\", overwriting", \
            num=str(line_number_debug), name=entry_name))
    f=open(target_path,'w', encoding="utf-8")
    f.write(entry_content+"\n")
def splitarray_to_string(split_content):
    final=""
    for phrase in split_content:
        final+=phrase+" "
    return final.strip()
def write_infofile(path,filename,content,line_number_debug, header_name_debug):
    if not os.path.isdir(path):
        os.makedirs(path)
    target_path=path+"/"+filename
    if os.path.isfile(target_path):
        handle_warning(fd.feof("repeated-header-warn", "Line {num}: repeated header info \"{name}\", overwriting", \
            num=str(line_number_debug), name=header_name_debug))
    f=open(target_path,'w', encoding="utf-8")
    f.write(content+'\n')

def write_infofile_newlines(path: str, filename: str, content_phrases: list[str], line_number_debug: int, header_name_debug: str):
    if not os.path.isdir(path):
        os.makedirs(path)
    target_path=path+"/"+filename
    if os.path.isfile(target_path):
        handle_warning(fd.feof("repeated-header-warn", "Line {num}: repeated header info \"{name}\", overwriting", \
            num=str(line_number_debug), name=header_name_debug))
    f=open(target_path,'w', encoding="utf-8")
    for line in content_phrases:
        f.write(line+"\n")

def generate_custom_path():
    # Generate a temporary path
    global path
    path=_globalvar.clitheme_temp_root+"/clitheme-temp-"
    for x in range(8):
        path+=random.choice(string.ascii_letters)

def generate_data_hierarchy(file_content: str, custom_path_gen=True, custom_infofile_name="1"):
    # make directories
    if custom_path_gen:
        generate_custom_path()
    if not os.path.exists(path): os.mkdir(path)
    datapath=path+"/"+_globalvar.generator_data_pathname
    if not os.path.exists(datapath): os.mkdir(datapath)

    # data to keep track of
    headerparsed=False
    mainparsed=False
    lines_data=file_content.splitlines()
    lineindex=-1 # counter extra +1 operation at beginning
    global_options={}

    # define check functions
    def check_enough_args(phrases: list[str], count: int):
        if len(phrases)<count:
            handle_error(fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase=phrases[0], num=str(lineindex+1)))
    def check_extra_args(phrases: list[str], count: int, use_exact_count: bool):
        not_pass: bool
        if use_exact_count: not_pass=len(phrases)!=count
        else: not_pass=len(phrases)>count
        if not_pass:
            handle_error(fd.feof("extra-arguments-err", "Extra arguments after \"{phrase}\" on line {num}", num=str(lineindex+1), phrase=phrases[0]))
    def is_ignore_line() -> bool:
        return lines_data[lineindex].strip()=="" or lines_data[lineindex].strip().startswith('#')

    # defined sub-processing functions
    def parse_options(options_data: list[str], merge_global_options: bool) -> dict:
        # value options: leadtabindents, leadspaces
        value_options=["leadtabindents", "leadspaces"]
        # on/off options: substesc, strictcmdmatch, exactcmdmatch (use no<...> to disable)
        bool_options=["substesc", "strictcmdmatch", "exactcmdmatch"]
        final_options={}
        if merge_global_options: nonlocal global_options; final_options=copy.copy(global_options)
        if len(options_data)==0: return final_options # return either empty data or pre-existing global options
        for each_option in options_data:
            option_name=re.sub(r"^(no)*(?P<name>.+?)(:.+)*$", r"\g<name>", each_option)
            option_name_preserve_no=re.sub(r"^(?P<name>.+?)(:.+)*$", r"\g<name>", each_option)
            if option_name in value_options:
                # must not begin with no
                if option_name_preserve_no.startswith("no"):
                    handle_error(fd.feof("unknown-option-err", "Unknown option \"{phrase}\" on line {num}", num=str(lineindex+1), phrase=option_name_preserve_no))
                # get value
                results=re.search(r"^(?P<name>.+?):(?P<value>.+)+$", each_option)
                value: int
                if results==None: # no value specified
                    handle_error(fd.feof("option-without-value-err", "No value specified for option \"{phrase}\" on line {num}", num=str(lineindex+1), phrase=option_name))
                else: 
                    try: value=int(results.groupdict()['value'])
                    except ValueError: handle_error(fd.feof("option-value-not-int-err", "The value specified for option \"{phrase}\" is not an integer on line {num}", num=str(lineindex+1), phrase=option_name))
                # set option
                final_options[option_name]=value
            elif option_name in bool_options:
                # if starts with no, set to false; else, set to true
                final_options[option_name]=not option_name_preserve_no.startswith("no")
            else:
                handle_error(fd.feof("unknown-option-err", "Unknown option \"{phrase}\" on line {num}", num=str(lineindex+1), phrase=option_name_preserve_no))
        return final_options 
    def handle_set_global_options(options_data: list[str]):
        # set options globally
        nonlocal global_options; global_options=parse_options(options_data, merge_global_options=True) 
    def handle_block_input(preserve_indents: bool, preserve_empty_lines: bool, end_phrase: str="end_block", disallow_cmdmatch_options: bool=True) -> str:
        nonlocal lineindex
        minspaces=math.inf
        blockinput_data=""
        while lineindex<len(lines_data)-1:
            lineindex+=1
            # read line
            line=lines_data[lineindex].rstrip()
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
        got_options=copy.copy(global_options)
        if len(lines_data[lineindex].split())>1:
            got_options=parse_options(lines_data[lineindex].split()[1:], merge_global_options=True)
        for option in got_options.keys():
            if option=="leadtabindents": 
                if not preserve_indents and option not in global_options.keys(): handle_error(fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(lineindex+1), phrase=option))
                # insert tabs at start of each line
                blockinput_data=re.sub(r"^", r"\t"*int(got_options['leadtabindents']), blockinput_data, flags=re.MULTILINE)
            elif option=="leadspaces":
                if not preserve_indents and option not in global_options.keys(): handle_error(fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(lineindex+1), phrase=option))
                # insert spaces at start of each line
                blockinput_data=re.sub(r"^", " "*int(got_options['leadspaces']), blockinput_data, flags=re.MULTILINE)
            elif option=="substesc":
                # substitute {{ESC}} with escape literal
                if got_options['substesc']==True: blockinput_data=re.sub(r"{{ESC}}", "\x1b", blockinput_data)
            elif disallow_cmdmatch_options:
                handle_error(fd.feof("option-not-allowed-err", "Option \"{phrase}\" not allowed here at line {num}", num=str(lineindex+1), phrase=option))
        return blockinput_data
    def handle_entry(entry_name: str, end_phrase: str):
        # expect locale, locale_block, end_entry
        nonlocal lineindex
        while lineindex<len(lines_data)-1:
            lineindex+=1
            if is_ignore_line(): continue
            phrases=lines_data[lineindex].split()
            if phrases[0]=="locale" or phrases[0].startswith("locale:"):
                content: str
                locale: str
                if phrases[0].startswith("locale:"):
                    check_enough_args(phrases, 2)
                    results=re.search(r"locale:(?P<locale>.+)", phrases[0])
                    if results==None:
                        handle_error(fd.feof("not-enough-args-err", "Not enough arguments for \"{phrase}\" at line {num}", phrase="locale:<locale>", num=str(lineindex+1)))
                    else:
                        locale=results.groupdict()['locale']
                    content=splitarray_to_string(phrases[1:])
                else:
                    check_enough_args(phrases, 3)
                    content=splitarray_to_string(phrases[2:])
                    locale=phrases[1]
                target_entry=copy.copy(entry_name)
                # substesc
                if "substesc" in global_options.keys() and global_options['substesc']==True:
                    content=re.sub(r"{{ESC}}", '\x1b', content)
                if locale!="default":
                    target_entry+="__"+locale
                add_entry(datapath, target_entry, content, lineindex+1)
            elif phrases[0]=="locale_block" or phrases[0]=="[locale]":
                check_enough_args(phrases, 2)
                locales=phrases[1:]
                content=handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase="[/locale]" if phrases[0]=="[locale]" else "end_block")
                for this_locale in locales:
                    suffix=""
                    if this_locale!="default":
                        suffix="__"+this_locale
                    add_entry(datapath, entry_name+suffix, content, lineindex+1)
            elif phrases[0]==end_phrase:
                check_extra_args(phrases, 1, use_exact_count=True)
                break
            else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
            

    while lineindex<len(lines_data)-1:
        lineindex+=1
        # ignore empty and comment lines
        if is_ignore_line(): continue
        first_phrase=lines_data[lineindex].split()[0]
        # process header and main sections here
        if first_phrase=="begin_header" or first_phrase==r"{header_section}":
            # avoid repeated block
            if headerparsed==True: 
                handle_error(fd.feof("repeated-header-err", "Repeated header block at line {num}", num=str(lineindex+1)))
            end_phrase="end_header" if first_phrase=="begin_header" else r"{/header_section}"
            # --Process header block--
            while lineindex<len(lines_data)-1:
                lineindex+=1
                if is_ignore_line(): continue
                phrases=lines_data[lineindex].split()
                # Expect name, description, description_block, version, locales, locales_block, supported_apps, supported_apps_block
                if phrases[0]=="name" or phrases[0]=="version" or phrases[0]=="description":
                    check_enough_args(phrases, 2)
                    content=splitarray_to_string(phrases[1:])
                    write_infofile( \
                        path+"/"+_globalvar.generator_info_pathname+"/"+custom_infofile_name, \
                        "clithemeinfo_"+phrases[0],\
                        content,lineindex+1,phrases[0]) # e.g. [...]/theme-info/1/clithemeinfo_name
                elif phrases[0]=="locales" or phrases[0]=="supported_apps":
                    check_enough_args(phrases, 2)
                    content=phrases[1:]
                    write_infofile_newlines( \
                        path+"/"+_globalvar.generator_info_pathname+"/"+custom_infofile_name, \
                        "clithemeinfo_"+phrases[0]+"_v2",\
                        content,lineindex+1,phrases[0]) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
                elif phrases[0]=="locales_block" or phrases[0]=="supported_apps_block" or phrases[0]=="description_block" or phrases[0]=="[locales]" or phrases[0]=="[supported_apps]" or phrases[0]=="[description]":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    # handle block input
                    content=""; filename=""
                    endphrase="end_block"
                    if not phrases[0].endswith("_block"): endphrase=phrases[0].replace("[", "[/")
                    if phrases[0]=="description_block":
                        content=handle_block_input(preserve_indents=True, preserve_empty_lines=True, end_phrase=endphrase)
                        filename=f"clithemeinfo_{re.sub(r'_block$', '', phrases[0]).replace('[','').replace(']','')}"
                    else:
                        content=handle_block_input(preserve_indents=False, preserve_empty_lines=False, end_phrase=endphrase)
                        filename=f"clithemeinfo_{re.sub(r'_block$', '', phrases[0]).replace('[','').replace(']','')}_v2"
                    write_infofile( \
                        path+"/"+_globalvar.generator_info_pathname+"/"+custom_infofile_name, \
                        filename,\
                        content,lineindex+1,re.sub(r'_block$','',phrases[0])) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
                elif phrases[0]==end_phrase:
                    check_extra_args(phrases, 1, use_exact_count=True)
                    headerparsed=True
                    break
                else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
            # END --Process header block--

        elif first_phrase=="begin_main" or first_phrase==r"{entries_section}":
            if mainparsed:
                handle_error(fd.feof("repeated-main-err", "Repeated main block at line {num}", num=str(lineindex+1)))
            end_phrase="end_main" if first_phrase=="begin_main" else r"{/entries_section}"
            if first_phrase=="begin_main":
                handle_warning(fd.feof("syntax-phrase-deprecation-warning", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=str(lineindex+1), old_phrase="begin_main", new_phrase=r"{entries_section}"))
            # --Process entries/main block--
            domainapp=""
            subsection=""
            while lineindex<len(lines_data)-1:
                lineindex+=1
                if is_ignore_line(): continue
                phrases=lines_data[lineindex].split()
                # expect entry, in_domainapp, in_subsction, unset_domainapp, unset_subsection
                if phrases[0]=="in_domainapp":
                    check_enough_args(phrases, 3)
                    check_extra_args(phrases, 3, use_exact_count=False)
                    if _globalvar.sanity_check(phrases[1]+" "+phrases[2])==False:
                        handle_error(fd.feof("sanity-check-domainapp-err", "Line {num}: domain and app names {sanitycheck_msg}", num=str(lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    domainapp=phrases[1]+" "+phrases[2]
                    subsection="" # clear subsection
                elif phrases[0]=="in_subsection":
                    check_enough_args(phrases, 2)
                    if _globalvar.sanity_check(splitarray_to_string(phrases[1:]))==False:
                        handle_error(fd.feof("sanity-check-subsection-err", "Line {num}: subsection names {sanitycheck_msg}", num=str(lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    subsection=splitarray_to_string(phrases[1:])
                elif phrases[0]=="unset_domainapp":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    domainapp=""; subsection=""
                elif phrases[0]=="unset_subsection":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    subsection=""
                elif phrases[0]=="entry" or phrases[0]=="[entry]":
                    check_enough_args(phrases, 2)
                    # Prevent leading . & prevent /,\ in entry name
                    if _globalvar.sanity_check(splitarray_to_string(phrases[1:]))==False:
                        handle_error(fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=str(lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    entry_name=splitarray_to_string(phrases[1:])
                    if subsection!="": entry_name=subsection+" "+entry_name
                    if domainapp!="": entry_name=domainapp+" "+entry_name
                    recursive_mkdir(datapath, entry_name, lineindex+1)
                    handle_entry(entry_name, end_phrase="[/entry]" if phrases[0]=="[entry]" else "end_entry")
                elif phrases[0]=="set_options":
                    check_enough_args(phrases, 2)
                    handle_set_global_options(phrases[1:])
                elif phrases[0]==end_phrase:
                    check_extra_args(phrases, 1, use_exact_count=True)
                    mainparsed=True
                    # deprecation warning
                    if phrases[0]=="end_main":
                        handle_warning(fd.feof("syntax-phrase-deprecation-warning", "Line {num}: phrase \"{old_phrase}\" is deprecated in this version; please use \"{new_phrase}\" instead", num=str(lineindex+1), old_phrase="end_main", new_phrase=r"{/entries_section}"))
                    break
                else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
            ## END --Process entries/main block--
    if not headerparsed or not mainparsed:
        handle_error(fd.reof("incomplete-block-err", "Missing or incomplete header or main block"))
    # Update current theme index
    theme_index=open(path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename, 'w', encoding="utf-8")
    theme_index.write(custom_infofile_name+"\n")

try:
    if not frontend.set_local_themedef(_get_resource.read_file("strings/generator-strings.clithemedef.txt")): raise RuntimeError()
    if not frontend.set_local_themedef(_get_resource.read_file("strings/cli-strings.clithemedef.txt"), overlay=True): raise RuntimeError()
except:
    if _version.release==0: print("generator set_local_themedef failed")
    pass