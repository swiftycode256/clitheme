import sys
import os
import sqlite3
import re
import copy
import uuid
from typing import Optional
from .. import _globalvar, frontend

connection=sqlite3.connect(":memory:") # placeholder
debug_mode=False
_globalvar.handle_set_themedef(frontend, "db_interface")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")

class need_db_regenerate(Exception):
    pass
class bad_pattern(Exception):
    pass

def handle_warning(message: str):
    if debug_mode: print(fd.feof("warning-str", "Warning: {msg}", msg=message))
def init_db(file_path: str):
    global connection
    connection=sqlite3.connect(file_path)
    # create the table
    # command_match_strictness: 0: default match options, 1: must start with pattern, 2: must exactly equal pattern
    # stdout_stderr_only: 0: no limiter, 1: match stdout only, 2: match stderr only
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename} ( \
                    match_pattern TEXT NOT NULL, \
                    substitute_pattern TEXT NOT NULL, \
                    is_regex INTEGER NOT NULL, \
                    unique_id TEXT NOT NULL, \
                    effective_command TEXT, \
                    effective_locale TEXT, \
                    command_match_strictness INTEGER NOT NULL, \
                    end_match_here INTEGER NOT NULL, \
                    stdout_stderr_only INTEGER NOT NULL \
                    );")
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename}_version (value INTEGER NOT NULL);")
    connection.execute(f"INSERT INTO {_globalvar.db_data_tablename}_version (value) VALUES (?)", (_globalvar.db_version,)) 
    connection.commit()
def connect_db():
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
        raise FileNotFoundError("No theme set or theme does not contain substrules")
    global connection
    connection=sqlite3.connect(f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}")
    # check db version
    version=int(connection.execute(f"SELECT value FROM {_globalvar.db_data_tablename}_version").fetchone()[0])
    if version!=_globalvar.db_version:
        raise need_db_regenerate

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: Optional[list[str]], effective_locale: Optional[str]=None, is_regex: bool=True, command_match_strictness: int=0, end_match_here: bool=False, stdout_stderr_matchoption: int=0, unique_id: uuid.UUID=uuid.uuid4(), line_number_debug: int=-1):
    cmdlist: list[str]=[]
    try: re.sub(match_pattern, substitute_pattern, "") # test if patterns are valid
    except: raise bad_pattern(str(sys.exc_info()[1]))
    # handle condition where no effective_locale is specified ("default")
    locale_condition="AND effective_locale=?" if effective_locale!=None else "AND typeof(effective_locale)=typeof(?)"
    insert_values=["match_pattern", "substitute_pattern", "effective_command", "is_regex", "command_match_strictness", "end_match_here", "effective_locale", "stdout_stderr_only", "unique_id"]
    if effective_commands!=None and len(effective_commands)>0: 
        for cmd in effective_commands:
            # remove extra spaces in the command
            cmdlist.append(re.sub(r" {2,}", " ", cmd).strip())
    else:
        # remove any existing values with the same match_pattern
        match_condition=f"match_pattern=? AND typeof(effective_command)=typeof(null) {locale_condition} AND stdout_stderr_only=? AND is_regex=?"
        match_params=(match_pattern, effective_locale, stdout_stderr_matchoption, is_regex)
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params).fetchall())>0:
            handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(insert_values)}) VALUES ({','.join('?'*len(insert_values))});", (match_pattern, substitute_pattern, None, is_regex, command_match_strictness, end_match_here, effective_locale, stdout_stderr_matchoption, str(unique_id)))
    for cmd in cmdlist:
        # remove any existing values with the same match_pattern and effective_command
        strictness_condition=""
        # if command_match_strictness==2: strictness_condition="AND command_match_strictness=2"
        match_condition=f"match_pattern=? AND effective_command=? {strictness_condition} {locale_condition} AND stdout_stderr_only=? AND is_regex=?"
        match_params=(match_pattern, cmd, effective_locale, stdout_stderr_matchoption, is_regex)
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params).fetchall())>0:
            handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(insert_values)}) VALUES ({','.join('?'*len(insert_values))});", (match_pattern, substitute_pattern, cmd, is_regex, command_match_strictness, end_match_here, effective_locale, stdout_stderr_matchoption, str(unique_id)))
    connection.commit()

def match_content(content: bytes, command: Optional[str]=None, is_stderr: bool=False) -> bytes:
    # Match order:
    # 1. Match rules with exactcmdmatch option set
    # 2. Match rules with command filter having the same first phrase
    #   - Command filters with greater number of phrases are prioritized over others
    # 3. Match rules without command filter

    # retrieve a list of effective commands matching first argument
    final_cmdlist=[]
    final_cmdlist_exactmatch=[]
    if command!=None and len(command.split())>0:
        # obtain a list of effective_command with the same first term
        cmdlist=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command LIKE ?;", (command.split()[0].strip()+" %",)).fetchall()
        # also include one-phrase commands
        cmdlist+=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command=?;", (command.split()[0].strip(),)).fetchall()
        # sort by number of phrases (greatest to least)
        def split_len(obj: tuple) -> int: return len(obj[0].split())
        cmdlist.sort(key=split_len, reverse=True)
        # prioritize effective_command with exact match requirement
        cmdlist=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command=? AND command_match_strictness=2", (re.sub(r" {2,}", " ", command).strip(),)).fetchall()+cmdlist
        def process_smartcmdmatch_phrases(match_cmd: str) -> list[str]:
            match_cmd_phrases=[]
            for p in range(len(match_cmd.split())):
                ph=match_cmd.split()[p]
                results=re.search(r"^-([^-]+)$",ph)
                if p>0 and results!=None:
                    for character in results.groups()[0]: match_cmd_phrases.append("-"+character)
                else: match_cmd_phrases.append(ph)
            return match_cmd_phrases
        # attempt to find matching command 
        for tp in cmdlist:
            match_cmd: str=tp[0].strip() # extract value from tuple
            strictness: int=tp[1] # strictness setting
            success=True
            if strictness==1: # must start with pattern in terms of space-separated phrases
                condition=len(match_cmd.split())<len(command.split()) and command.split()[:len(match_cmd.split())]==match_cmd.split()
                if not condition==True: success=False
            elif strictness==2: # must equal to pattern
                if not re.sub(r" {2,}", " ", command).strip()==match_cmd: success=False
            elif strictness==-1: # smartcmdmatch: split phrases starting with one '-' and split them. Then, perform strictness==0 operation
                # process both phrases
                match_cmd_phrases=process_smartcmdmatch_phrases(match_cmd)
                command_phrases=process_smartcmdmatch_phrases(command)
                for phrase in match_cmd_phrases:
                    if phrase not in command_phrases: success=False
            else: # implying strictness==0; must contain all phrases in pattern
                for phrase in match_cmd.split():
                    if phrase not in command.split(): success=False
            if success:
                # if found matching command
                if match_cmd not in final_cmdlist: 
                    final_cmdlist.append(match_cmd)
                    final_cmdlist_exactmatch.append(strictness==2)

    content_str=copy.copy(content)
    matches=[]
    def fetch_matches_by_locale(filter_condition: str, filter_data: tuple=tuple()):
        fetch_items=["match_pattern", "substitute_pattern", "is_regex", "end_match_here", "stdout_stderr_only", "unique_id"]
        # get locales
        locales=_globalvar.get_locale()
        nonlocal matches
        # try the ones with locale defined
        for this_locale in locales:
            fetch_data=connection.execute(f"SELECT DISTINCT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE {filter_condition} AND effective_locale=? ORDER BY rowid;", filter_data+(this_locale,)).fetchall()
            if len(fetch_data)>0:
                matches+=fetch_data
                return
        # else, fetches the ones without locale defined
        matches+=connection.execute(f"SELECT DISTINCT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE {filter_condition} AND typeof(effective_locale)=typeof(null) ORDER BY rowid;", filter_data).fetchall()
    if len(final_cmdlist)>0:
        for x in range(len(final_cmdlist)):
            cmd=final_cmdlist[x]
            # prioritize exact match
            if final_cmdlist_exactmatch[x]==True: fetch_matches_by_locale("effective_command=? AND command_match_strictness=2", (cmd,))
            # also append matches with other strictness
            fetch_matches_by_locale("effective_command=? AND command_match_strictness!=2", (cmd,))
    fetch_matches_by_locale("typeof(effective_command)=typeof(null)")
    encountered_ids=set()
    for match_data in matches:
        if match_data[4]!=0 and is_stderr+1!=match_data[4]: continue # check stdout/stderr constraint
        if match_data[5] in encountered_ids: continue
        else: encountered_ids.add(match_data[5])
        matched=False
        try:
            if match_data[2]==True: # is regex 
                try: 
                    matched=re.search(match_data[0], content_str.decode('utf-8'))!=None
                    content_str=bytes(re.sub(match_data[0], match_data[1], content_str.decode('utf-8')), 'utf-8')
                except UnicodeDecodeError: 
                    matched=re.search(bytes(match_data[0], 'utf-8'), content_str)!=None                    
                    content_str=re.sub(bytes(match_data[0],'utf-8'), bytes(match_data[1], 'utf-8'), content_str)
            else: # is string
                try: 
                    matched=match_data[0] in content_str.decode('utf-8')
                    content_str=bytes(content_str.decode('utf-8').replace(match_data[0], match_data[1]), 'utf-8')
                except UnicodeDecodeError: 
                    matched=bytes(match_data[0], 'utf-8') in content_str
                    content_str=content_str.replace(bytes(match_data[0],'utf-8'), bytes(match_data[1],'utf-8'))
            if match_data[3]==True and matched: # endmatchhere is set
                break
        except:
            handle_warning("Error occurred while matching string: "+str(sys.exc_info()[1]))
    return content_str