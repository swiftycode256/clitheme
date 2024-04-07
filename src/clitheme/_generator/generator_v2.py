"""
Generator function used in applying themes (should not be invoked directly)
"""
import os
import string
import random
import re
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

    # defined sub-processing functions
    def handle_block_input(preserve_indents: bool, preserve_empty_lines: bool, end_phrase: str="end_block") -> str:
        nonlocal lineindex
        minspaces=0
        blockinput_data=""
        while lineindex<len(lines_data):
            lineindex+=1
            if lines_data[lineindex].split()[0]==end_phrase: break
            # read line
            line=lines_data[lineindex].rstrip()
            if line.strip()=="": # empty line
                if preserve_empty_lines: blockinput_data+="\n"
                continue
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
                    line=leading_whitespace+re.sub(r"^\\([\\]*)end_block", r"\g<1>end_block", line.strip())
                    # update minspaces
                    minspaces=min(minspaces, len(leading_whitespace))
            else: # don't preserve whitespaces
                line=re.sub(r"^\\([\\]*)end_block", r"\g<1>end_block", line.strip())
            # write to data
            blockinput_data+="\n"+line
        # remove the extra leading newline
        blockinput_data=re.sub(r"\A\n", "", blockinput_data)
        # remove all whitespaces except common minspaces (if preserve_indents)
        if preserve_indents:
            pattern=r"(?P<optline>\n|^)[ ]{"+str(minspaces)+"}"
            blockinput_data=re.sub(pattern,r"\g<optline>", blockinput_data)
        return blockinput_data
    def handle_entry(entry_name: str):
        # expect locale, locale_block, end_entry
        nonlocal lineindex
        while lineindex<len(lines_data):
            lineindex+=1
            if lines_data[lineindex].strip()=="" or lines_data[lineindex].strip().startswith('#'): 
                lineindex+=1; continue
            phrases=lines_data[lineindex].split()
            if phrases[0]=="locale":
                check_enough_args(phrases, 3)
                content=splitarray_to_string(phrases[2:])
                target_entry=entry_name
                if phrases[1]!="default":
                    target_entry+="__"+phrases[1]
                add_entry(datapath, target_entry, content, lineindex+1)
            elif phrases[0]=="locale_block":
                check_enough_args(phrases, 2)
                locales=phrases[1:]
                content=handle_block_input(preserve_indents=True, preserve_empty_lines=True)
                for this_locale in locales:
                    suffix=""
                    if this_locale!="default":
                        suffix="__"+this_locale
                    add_entry(datapath, entry_name+suffix, content, lineindex+1)
            elif phrases[0]=="end_entry":
                check_extra_args(phrases, 1, use_exact_count=True)
                break
            else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
            

    while lineindex<len(lines_data):
        lineindex+=1
        # ignore empty and comment lines
        if lines_data[lineindex].strip()=="" or lines_data[lineindex].strip().startswith('#'): 
            lineindex+=1; continue
        # process header and main sections here
        if lines_data[lineindex].split()[0]=="begin_header":
            # avoid repeated block
            if headerparsed==True: 
                handle_error(fd.feof("repeated-header-err", "Repeated header block at line {num}", num=str(lineindex+1)))
            # --Process header block--
            while lineindex<len(lines_data):
                lineindex+=1
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
                elif phrases[0]=="locales_block" or phrases[0]=="supported_apps_block" or phrases[0]=="description_block":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    # handle block input
                    content=""; filename=""
                    if phrases[0]=="description_block":
                        content=handle_block_input(preserve_indents=True, preserve_empty_lines=True)
                        filename=f"clithemeinfo_{re.sub(r'_block$', '', phrases[0])}"
                    else:
                        content=handle_block_input(preserve_indents=False, preserve_empty_lines=False)
                        filename=f"clithemeinfo_{re.sub(r'_block$', '', phrases[0])}_v2"
                    write_infofile( \
                        path+"/"+_globalvar.generator_info_pathname+"/"+custom_infofile_name, \
                        filename,\
                        content,lineindex+1,re.sub(r'_block$','',phrases[0])) # e.g. [...]/theme-info/1/clithemeinfo_description_v2
                elif phrases[0]=="end_header":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    headerparsed=True
                    break
                else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
            # END --Process header block--

        elif lines_data[lineindex].split()[0]=="begin_main":
            if mainparsed:
                handle_error(fd.feof("repeated-main-err", "Repeated main block at line {num}", num=str(lineindex+1)))
            # --Process main block--
            domainapp=""
            subsection=""
            while lineindex<len(lines_data):
                lineindex+=1
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
                elif phrases[0]=="entry":
                    check_enough_args(phrases, 2)
                    # Prevent leading . & prevent /,\ in entry name
                    if _globalvar.sanity_check(splitarray_to_string(phrases[1:]))==False:
                        handle_error(fd.feof("sanity-check-entry-err", "Line {num}: entry subsections/names {sanitycheck_msg}", num=str(lineindex+1), sanitycheck_msg=_globalvar.sanity_check_error_message))
                    entry_name=splitarray_to_string(phrases[1:])
                    if subsection!="": entry_name=subsection+" "+entry_name
                    if domainapp!="": entry_name=domainapp+" "+entry_name
                    recursive_mkdir(datapath, entry_name, lineindex+1)
                    handle_entry(entry_name)
                elif phrases[0]=="end_main":
                    check_extra_args(phrases, 1, use_exact_count=True)
                    mainparsed=True
                    break
                else: handle_error(fd.feof("invalid-phrase-err", "Unexpected \"{phrase}\" on line {num}", phrase=phrases[0], num=str(lineindex+1)))
    if not headerparsed or not mainparsed:
        handle_error(fd.reof("incomplete-block-err", "Missing or incomplete header or main block"))
    # Update current theme index
    theme_index=open(path+"/"+_globalvar.generator_info_pathname+"/"+_globalvar.generator_index_filename, 'w', encoding="utf-8")
    theme_index.write(custom_infofile_name+"\n")

try:
    if not frontend.set_local_themedef(_get_resource.read_file("strings/generator-strings.clithemedef.txt")): raise RuntimeError()
except:
    if _version.release==0: print("generator set_local_themedef failed")
    pass