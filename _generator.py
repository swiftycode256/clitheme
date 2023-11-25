import os,sys
import string
import random
import warnings

header_begin=\
    """# clitheme theme info header
    # This file is automatically generated by clitheme and should not be edited
    """

path="" # to be generated by function

def handle_error(message):
    raise SyntaxError(message)
def handle_warning(message):
    warnings.warn(message,SyntaxWarning)
def recursive_mkdir(path, entry_name, line_number_debug): # recursively generate directories (excluding file itself)
    current_path=path
    current_entry="" # for error output
    for x in entry_name.split()[:-1]:
        current_entry+=x+" "
        current_path+="/"+x
        if os.path.isfile(current_path): # conflict with entry file
            handle_error("Line "+str(line_number_debug)+": cannot create subsection \""+current_entry+"\" because an entry with the same name already exists")
        elif os.path.isdir(str(current_path))==False: # directory does not exist
           os.mkdir(current_path) 
def add_entry(path, entry_name, entry_content, line_number_debug): # add entry to where it belongs (assuming recursive_mkdir already completed)
    target_path=path
    for x in entry_name.split():
        target_path+="/"+x
    if os.path.isdir(target_path):
        handle_error("Line "+str(line_number_debug)+": cannot create entry \""+entry_name+"\" because a subsection with the same name already exists")
    elif os.path.isfile(target_path):
        handle_warning("Line "+str(line_number_debug)+": repeated entry \""+entry_name+"\", overwriting")
    f=open(target_path,'w')
    f.write(entry_content+"\n")
def splitarray_to_string(split_content):
    final=""
    for phrase in split_content:
        final+=phrase+" "
    return final.strip()
def write_infofile(path,filename,content,line_number_debug, header_name_debug):
    target_path=path+"/"+filename
    if os.path.isfile(target_path):
        handle_warning("Line "+str(line_number_debug)+": repeated header info \""+header_name_debug+"\", overwriting")
    f=open(target_path,'w')
    f.write(content+'\n')
# Returns true for success or error message
def generate_data_hierarchy(file_content):
    """Generate the data hierarchy in a temperory directory from a definition file (accessible with _generator.path)"""
    # Generate a temporary path
    global path
    path="/tmp/clitheme-temp-"
    for x in range(8):
        path+=random.choice(string.ascii_letters)
    os.mkdir(path)
    datapath=path+"/theme-data"
    os.mkdir(datapath)
    # headerinfo_file=open(path+"/current-theme.clithemeheader",'x')
    # headerinfo_file.write(header_begin)
    current_status="" # header, main, entry
    linenumber=0
    # To detect repeated blocks
    headerparsed=False
    mainparsed=False
    current_domainapp="" # for in_domainapp and unset_domainapp in main block
    current_entry_name="" # for entry
    for line in file_content.splitlines():
        linenumber+=1
        phrases=line.split()
        if line.strip()=="" or line.strip()[0]=="#": # if empty line or comment
            continue
        if current_status=="": # expect begin_header or begin_main
            if line.strip()=="begin_header": 
                if headerparsed:
                    handle_error("Repeated header block at line "+str(linenumber))
                current_status="header"
            elif line.strip()=="begin_main": 
                if mainparsed:
                    handle_error("Repeated main block at line "+str(linenumber))
                current_status="main"
            elif (phrases[0]=="begin_header" or phrases[0]=="begin_main") and len(phrases)>1: # extra arguments
                handle_error("Unexpected arguments after \""+phrases[0]+"\" on line "+str(linenumber))
            else: handle_error("Unexpected \""+phrases[0]+"\" on line "+str(linenumber))
        elif current_status=="header": # expect name, version, locales, or end_header
            if phrases[0]=="name" or phrases[0]=="version" or phrases[0]=="locales":
                # headerinfo_file.write(line.strip()+"\n")                
                content=splitarray_to_string(phrases[1:])
                write_infofile(path, "clithemeinfo_"+phrases[0],content,linenumber,phrases[0])
            elif line.strip()=="end_header": 
                current_status=""
                headerparsed=True
            elif (phrases[0]=="end_header") and len(phrases)>1: # extra arguments
                handle_error("Extra arguments after \""+phrases[0]+"\" on line "+str(linenumber))
            else: handle_error("Unexpected \""+phrases[0]+"\" on line "+str(linenumber))
        elif current_status=="main": # expect entry, in_domainapp, unset_domainapp, end_main
            if phrases[0]=="entry":
                # if len(phrases)<3:
                #     handle_error("Not enough arguments for "+phrases[0]+" line at line "+str(linenumber))
                entry_name=splitarray_to_string(phrases[1:]) # generate entry name
                if current_domainapp!="": entry_name=current_domainapp+" "+entry_name
                recursive_mkdir(datapath, entry_name, linenumber)
                current_status="entry"
                current_entry_name=entry_name
            elif phrases[0]=="in_domainapp": 
                if len(phrases)!=3:
                    handle_error("Format error in "+phrases[0]+" at line "+linenumber)
                current_domainapp=phrases[1]+" "+phrases[2]
            elif phrases[0]=="unset_domainapp":
                if len(phrases)!=1:
                    handle_error("Extra arguments after \""+phrases[0]+"\" on line "+str(linenumber))
                current_domainapp=""
            elif phrases[0]=="end_main":
                if len(phrases)!=1:
                    handle_error("Extra arguments after \""+phrases[0]+"\" on line "+str(linenumber))
                current_status=""
                mainparsed=True
            else: handle_error("Unexpected \""+phrases[0]+"\" on line "+str(linenumber))
        elif current_status=="entry": # expect locale, end_entry
            if phrases[0]=="locale":
                content=splitarray_to_string(phrases[2:])
                target_entry=current_entry_name
                if phrases[1]!="default":
                    target_entry+="__"+phrases[1]
                add_entry(datapath,target_entry,content,linenumber)
            elif phrases[0]=="end_entry":
                if len(phrases)!=1:
                    handle_error("Extra arguments after \""+phrases[0]+"\" on line "+str(linenumber))
                current_status="main"
            else: handle_error("Unexpected \""+phrases[0]+"\" on line "+str(linenumber))
    if not headerparsed or not mainparsed:
        handle_error("Missing or incomplete header or main block")
    return True # Everything is successul! :)