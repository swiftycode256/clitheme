import sys
import sqlite3
import re
import copy
from typing import Optional
try: from .. import _globalvar
except ImportError: import _globalvar

connection=sqlite3.connect(":memory:") # placeholder
def init_db(file_path: str):
    global connection
    connection=sqlite3.connect(file_path)
    # create the table
    # command_match_strictness: 0:default match options, 1:must start with pattern, 2: must exactly equal pattern
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename} ( \
                    match_pattern TEXT NOT NULL, \
                    substitute_pattern TEXT NOT NULL, \
                    is_regex INTEGER DEFAULT true NOT NULL, \
                    effective_command TEXT, \
                    command_match_strictness INTEGER DEFAULT 0 NOT NULL, \
                    end_match_here INTEGER DEFAULT 0 NOT NULL \
                    );")
    connection.commit()

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: Optional[list[str]], is_regex: bool=True, command_match_strictness: int=0, end_match_here: bool=False, line_number_debug: int=-1):
    global cursor
    cmdlist=[]
    if effective_commands!=None and len(effective_commands)>0: 
        for cmd in effective_commands:
            # remove extra spaces in the command
            cmdlist.append(re.sub(r" {2,}", " ", cmd).strip())
    else:
        # remove any existing values with the same match_pattern
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND typeof(effective_command)=typeof(null);", (match_pattern.strip(),)).fetchall())>0:
            print(f"Warning: Repeated entry at line {line_number_debug}, overwriting")
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND typeof(effective_command)=typeof(null);", (match_pattern.strip(),))
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} (match_pattern, substitute_pattern, is_regex, command_match_strictness, end_match_here) VALUES (?,?,?,?,?);", (match_pattern.strip(), substitute_pattern.strip(), is_regex, command_match_strictness, end_match_here))
    for cmd in cmdlist:
        # remove any existing values with the same match_pattern and effective_command and command_match_strictness(if ==2)
        extra_condition=""
        if command_match_strictness==2: extra_condition=" AND command_match_strictness=2"
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND effective_command=?{extra_condition};", (match_pattern.strip(),cmd)).fetchall())>0:
            print(f"Warning: Repeated entry at line {line_number_debug}, overwriting")
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND effective_command=?{extra_condition};", (match_pattern.strip(),cmd))
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} (match_pattern, substitute_pattern, effective_command, is_regex, command_match_strictness, end_match_here) VALUES (?,?,?,?,?,?);", (match_pattern.strip(), substitute_pattern.strip(), cmd, is_regex, command_match_strictness, end_match_here))
    connection.commit()

def match_content(content: bytes, command: Optional[str]=None) -> bytes:
    # Match order:
    # 1. Match rules with exactcmdmatch option set
    # 2. Match rules with command filter having the same first phrase
    #   - Command filters with greater number of phrases are prioritized over others
    # 3. Match rules without command filter

    # retrieve a list of effective commands matching first argument
    final_cmdlist=[]
    final_cmdlist_strictmatch=[]
    if command!=None and len(command.split())>0:
        # obtain a list of effective_command with the same first term
        cmdlist=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command LIKE ?;", (command.split()[0].strip()+" %",)).fetchall()
        # also include one-phrase commands
        cmdlist+=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command=?;", (command.split()[0].strip(),)).fetchall()
        # sort by number of phrases (greatest to least)
        def split_len(obj: tuple) -> int: return len(obj[0].split())
        cmdlist.sort(key=split_len, reverse=True)
        # prioritize effective_command with exact match requirement
        cmdlist=connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command=? AND command_match_strictness=2", (command.strip(),)).fetchall()+cmdlist
        # attempt to find matching command 
        for tp in cmdlist:
            cmd=tp[0] # extract value from tuple
            strictness=tp[1] # strictness setting
            success=True
            if strictness==1: # must start with pattern
                if not command.startswith(cmd): success=False
            elif strictness==2: # must equal to pattern
                if not command==cmd: success=False
            else: # implying strictness==0; must contain all phrases in pattern
                for phrase in cmd.split():
                    if phrase not in command.split():
                        success=False; break
            if success:
                # if found matching command
                if cmd not in final_cmdlist: final_cmdlist.append(cmd)
                final_cmdlist_strictmatch.append(strictness==2)
                break
    content_str=copy.copy(content)
    matches=[]
    if len(final_cmdlist)>0:
        for x in range(len(final_cmdlist)):
            cmd=final_cmdlist[x]
            # prioritize exact match
            if final_cmdlist_strictmatch[x]==True: matches+=connection.execute(f"SELECT match_pattern, substitute_pattern, is_regex, end_match_here FROM {_globalvar.db_data_tablename} WHERE effective_command=? AND command_match_strictness=2 ORDER BY rowid;", (cmd,)).fetchall()
            matches+=connection.execute(f"SELECT match_pattern, substitute_pattern, is_regex, end_match_here FROM {_globalvar.db_data_tablename} WHERE effective_command=? ORDER BY rowid;", (cmd,)).fetchall()
    matches+=connection.execute(f"SELECT match_pattern, substitute_pattern, is_regex, end_match_here FROM {_globalvar.db_data_tablename} WHERE typeof(effective_command)=typeof(null) ORDER BY rowid;").fetchall()
    for match_data in matches:
        try:
            if match_data[2]==True: # is regex 
                content_str=re.sub(bytes(match_data[0],'utf-8'), bytes(match_data[1], 'utf-8'), content_str)
            else: # is string
                content_str=content_str.replace(bytes(match_data[0],'utf-8'), bytes(match_data[1],'utf-8'))
        except:
            print("Error occurred while matching string: ", end="")
            print(sys.exc_info()[1])
        if match_data[3]==True: # endmatchoption is set
            break
    return content_str