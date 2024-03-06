import sys
import sqlite3
import re
from typing import Optional
try: from .. import _globalvar
except ImportError: import _globalvar

connection=sqlite3.connect(":memory:") # placeholder
def init_db(file_path: str):
    global connection
    connection=sqlite3.connect(file_path)
    # create the table
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename} ( \
                    match_pattern TEXT NOT NULL, \
                    substitute_pattern TEXT NOT NULL, \
                    is_regex INTEGER DEFAULT true NOT NULL, \
                    effective_command TEXT \
                    );")
    connection.commit()

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: Optional[list[str]], is_regex: bool=True):
    global cursor
    cmdlist=[]
    if effective_commands!=None and len(effective_commands)>0: 
        for cmd in effective_commands:
            # remove extra spaces in the command
            cmdlist.append(re.sub(r" {2,}", " ", cmd).strip())
    else:
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND typeof(effective_command)=typeof(null);", (match_pattern.strip(),)).fetchall())>0:
            print("Warning: Repeated entry at line %, overwriting")
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND typeof(effective_command)=typeof(null);", (match_pattern.strip(),))
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} (match_pattern, substitute_pattern, is_regex) VALUES (?,?,?);", (match_pattern.strip(), substitute_pattern.strip(), is_regex))
    for cmd in cmdlist:
        # remove any existing values with the match_pattern and effective_command, if any
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND effective_command=?;", (match_pattern.strip(),cmd)).fetchall())>0:
            print("Warning: Repeated entry at line %, overwriting")
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE match_pattern=? AND effective_command=?;", (match_pattern.strip(),cmd))
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} (match_pattern, substitute_pattern, effective_command, is_regex) VALUES (?,?,?,?);", (match_pattern.strip(), substitute_pattern.strip(), cmd, is_regex))
    connection.commit()

def match_content(content: bytes, command: Optional[str]=None) -> bytes:
    # retrieve a list of effective commands matching first argument
    target_command=None
    if command!=None and len(command.split())>0:
        cmdlist=connection.execute(f"SELECT DISTINCT effective_command FROM {_globalvar.db_data_tablename} WHERE effective_command LIKE ?;", (command.split()[0].strip()+" %",)).fetchall()
        # also include one-phrase effective commands
        cmdlist+=connection.execute(f"SELECT DISTINCT effective_command FROM {_globalvar.db_data_tablename} WHERE effective_command=?;", (command.split()[0].strip(),)).fetchall()
        # sort by command length (greatest to least)
        cmdlist.sort(key=len, reverse=True)
        # attempt to find matching command 
        for tp in cmdlist:
            cmd=tp[0] # extract value from tuple
            success=True
            for phrase in cmd.split():
                if phrase not in command.split():
                    success=False; break
            if success:
                # if found matching command
                target_command=cmd
                break
    content_str=content
    matches=[]
    if target_command!=None: matches+=connection.execute(f"SELECT match_pattern, substitute_pattern, is_regex FROM {_globalvar.db_data_tablename} WHERE effective_command=? ORDER BY rowid;", (target_command,)).fetchall()
    matches+=connection.execute(f"SELECT match_pattern, substitute_pattern, is_regex FROM {_globalvar.db_data_tablename} WHERE typeof(effective_command)=typeof(null) ORDER BY rowid;").fetchall()
    for match_data in matches:
        try:
            if match_data[2]==True: # is regex 
                content_str=re.sub(bytes(match_data[0],'utf-8'), bytes(match_data[1], 'utf-8'), content_str)
            else:
                content_str=content_str.replace(bytes(match_data[0],'utf-8'), bytes(match_data[1],'utf-8'))
        except:
            print("Error occurred while matching string: ", end="")
            print(sys.exc_info()[1])
    return content_str