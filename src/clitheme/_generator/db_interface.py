# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Interface for adding and matching substitution entries in database (internal module)
"""

import sys
import os
import sqlite3
import re
import copy
import uuid
from typing import Optional
from .. import _globalvar, frontend

# spell-checker:ignore matchoption cmdlist exactmatch rowid pids tcpgrp

connection=sqlite3.connect(":memory:") # placeholder
db_path=""
debug_mode=False
_globalvar.handle_set_themedef(frontend, "db_interface")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")

class need_db_regenerate(Exception):
    pass
class bad_pattern(Exception):
    pass

def _handle_warning(message: str):
    if debug_mode: print(fd.feof("warning-str", "Warning: {msg}", msg=message))
def init_db(file_path: str):
    global connection, db_path
    db_path=file_path
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
                    foreground_only INTEGER NOT NULL, \
                    end_match_here INTEGER NOT NULL, \
                    stdout_stderr_only INTEGER NOT NULL \
                    );")
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename}_version (value INTEGER NOT NULL);")
    connection.execute(f"INSERT INTO {_globalvar.db_data_tablename}_version (value) VALUES (?)", (_globalvar.db_version,)) 
    connection.commit()
def connect_db(path: str=f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
    global db_path
    db_path=path
    if not os.path.exists(path):
        raise FileNotFoundError("No theme set or theme does not contain substrules")
    global connection
    connection=sqlite3.connect(db_path)
    # check db version
    version=int(connection.execute(f"SELECT value FROM {_globalvar.db_data_tablename}_version").fetchone()[0])
    if version!=_globalvar.db_version:
        raise need_db_regenerate

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: Optional[list], effective_locale: Optional[str]=None, is_regex: bool=True, command_match_strictness: int=0, end_match_here: bool=False, stdout_stderr_matchoption: int=0, foreground_only: bool=False, unique_id: uuid.UUID=uuid.UUID(int=0), line_number_debug: str="-1"):
    if unique_id==uuid.UUID(int=0): unique_id=uuid.uuid4()
    cmdlist: list=[]
    try: re.sub(match_pattern, substitute_pattern, "") # test if patterns are valid
    except: raise bad_pattern(str(sys.exc_info()[1]))
    # handle condition where no effective_locale is specified ("default")
    locale_condition="AND effective_locale=?" if effective_locale!=None else "AND typeof(effective_locale)=typeof(?)"
    insert_values=["match_pattern", "substitute_pattern", "effective_command", "is_regex", "command_match_strictness", "end_match_here", "effective_locale", "stdout_stderr_only", "unique_id", "foreground_only"]
    if effective_commands!=None and len(effective_commands)>0: 
        for cmd in effective_commands:
            # remove extra spaces in the command
            cmdlist.append(re.sub(r" {2,}", " ", cmd).strip())
    else:
        # remove any existing values with the same match_pattern
        match_condition=f"match_pattern=? AND typeof(effective_command)=typeof(null) {locale_condition} AND stdout_stderr_only=? AND is_regex=?"
        match_params=(match_pattern, effective_locale, stdout_stderr_matchoption, is_regex)
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params).fetchall())>0:
            _handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(insert_values)}) VALUES ({','.join('?'*len(insert_values))});", (match_pattern, substitute_pattern, None, is_regex, command_match_strictness, end_match_here, effective_locale, stdout_stderr_matchoption, str(unique_id), foreground_only))
    for cmd in cmdlist:
        # remove any existing values with the same match_pattern and effective_command
        strictness_condition=""
        # if command_match_strictness==2: strictness_condition="AND command_match_strictness=2"
        match_condition=f"match_pattern=? AND effective_command=? {strictness_condition} {locale_condition} AND stdout_stderr_only=? AND is_regex=?"
        match_params=(match_pattern, cmd, effective_locale, stdout_stderr_matchoption, is_regex)
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params).fetchall())>0:
            _handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(insert_values)}) VALUES ({','.join('?'*len(insert_values))});", (match_pattern, substitute_pattern, cmd, is_regex, command_match_strictness, end_match_here, effective_locale, stdout_stderr_matchoption, str(unique_id), foreground_only))
    connection.commit()

def _check_strictness(match_cmd: str, strictness: int, target_command: str):
    def process_smartcmdmatch_phrases(match_cmd: str) -> list:
        match_cmd_phrases=[]
        for p in range(len(match_cmd.split())):
            ph=match_cmd.split()[p]
            results=re.search(r"^-([^-]+)$",ph)
            if p>0 and results!=None:
                for character in results.groups()[0]: match_cmd_phrases.append("-"+character)
            else: match_cmd_phrases.append(ph)
        return match_cmd_phrases
    success=True
    if strictness==1: # must start with pattern in terms of space-separated phrases
        condition=len(match_cmd.split())<=len(target_command.split()) and target_command.split()[:len(match_cmd.split())]==match_cmd.split()
        if not condition==True: success=False
    elif strictness==2: # must equal to pattern
        if not re.sub(r" {2,}", " ", target_command).strip()==match_cmd: success=False
    elif strictness==-1: # smartcmdmatch: split phrases starting with one '-' and split them. Then, perform strictness==0 operation
        # process both phrases
        match_cmd_phrases=process_smartcmdmatch_phrases(match_cmd)
        command_phrases=process_smartcmdmatch_phrases(target_command)
        for phrase in match_cmd_phrases:
            if phrase not in command_phrases: success=False
    else: # implying strictness==0; must contain all phrases in pattern
        for phrase in match_cmd.split():
            if phrase not in target_command.split(): success=False
    return success

def match_content(content: bytes, command: Optional[str]=None, is_stderr: bool=False, pids: tuple=(-1,-1)) -> bytes:
    # pids: (main_pid, current_tcpgrp)

    # Match order:
    # 1. Match rules with exactcmdmatch option set
    # 2. Match rules with command filter having the same first phrase
    #   - Command filters with greater number of phrases are prioritized over others
    # 3. Match rules without command filter

    # retrieve a list of effective commands matching first argument
    if not os.path.exists(db_path): raise sqlite3.OperationalError("file at db_path does not exist")
    _connection=sqlite3.connect(db_path)
    final_cmdlist=[]
    final_cmdlist_exactmatch=[]
    if command!=None and len(command.split())>0:
        # command without paths (e.g. /usr/bin/bash -> bash)
        stripped_command=os.path.basename(command.split()[0])+(" "+_globalvar.splitarray_to_string(command.split()[1:]) if len(command.split())>1 else '')
        cmdlist_items=["effective_command", "command_match_strictness"]
        # obtain a list of effective_command with the same first term
        cmdlist=_connection.execute(f"SELECT DISTINCT {','.join(cmdlist_items)} FROM {_globalvar.db_data_tablename} WHERE effective_command LIKE ? or effective_command LIKE ?;", (command.split()[0].strip()+" %", stripped_command.split()[0].strip()+" %")).fetchall()
        # also include one-phrase commands
        cmdlist+=_connection.execute(f"SELECT DISTINCT {','.join(cmdlist_items)} FROM {_globalvar.db_data_tablename} WHERE effective_command=? or effective_command=?;", (command.split()[0].strip(),stripped_command.split()[0].strip())).fetchall()
        # sort by number of phrases (greatest to least)
        def split_len(obj: tuple) -> int: return len(obj[0].split())
        cmdlist.sort(key=split_len, reverse=True)
        # prioritize effective_command with exact match requirement
        cmdlist=_connection.execute(f"SELECT DISTINCT {','.join(cmdlist_items)} FROM {_globalvar.db_data_tablename} WHERE (effective_command=? OR effective_command=?) AND command_match_strictness=2", (re.sub(r" {2,}", " ", command).strip(),re.sub(r" {2,}", " ", stripped_command).strip())).fetchall()+cmdlist
        # attempt to find matching command 
        for target_command in [command, stripped_command]:
            for tp in cmdlist:
                match_cmd=tp[0].strip()
                strictness=tp[1]
                if _check_strictness(match_cmd, strictness, target_command)==True:
                    # if found matching target_command
                    if match_cmd not in final_cmdlist: 
                        final_cmdlist.append(match_cmd)
                        final_cmdlist_exactmatch.append(strictness==2)

    content_str=copy.copy(content)
    matches=[]
    def fetch_matches_by_locale(filter_condition: str, filter_data: tuple=tuple()):
        fetch_items=["match_pattern", "substitute_pattern", "is_regex", "end_match_here", "stdout_stderr_only", "unique_id", "foreground_only", "effective_command", "command_match_strictness"]
        # get locales
        locales=_globalvar.get_locale()
        nonlocal matches
        # try the ones with locale defined
        for this_locale in locales:
            fetch_data=_connection.execute(f"SELECT DISTINCT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE {filter_condition} AND effective_locale=? ORDER BY rowid;", filter_data+(this_locale,)).fetchall()
            if len(fetch_data)>0:
                matches+=fetch_data
        # else, fetches the ones without locale defined
        matches+=_connection.execute(f"SELECT DISTINCT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE {filter_condition} AND typeof(effective_locale)=typeof(null) ORDER BY rowid;", filter_data).fetchall()
    if len(final_cmdlist)>0:
        for x in range(len(final_cmdlist)):
            cmd=final_cmdlist[x]
            # prioritize exact match
            if final_cmdlist_exactmatch[x]==True: fetch_matches_by_locale("effective_command=? AND command_match_strictness=2", (cmd,))
            # also append matches with other strictness
            fetch_matches_by_locale("effective_command=? AND command_match_strictness!=2", (cmd,))
    fetch_matches_by_locale("typeof(effective_command)=typeof(null)")
    content_str=_handle_subst(matches, content_str, is_stderr, pids, command)
    return content_str

# timeout value for each match operation
match_timeout=_globalvar.output_subst_timeout

def _handle_subst(matches: list, content: bytes, is_stderr: bool, pids: tuple, target_command: Optional[str]):
    content_str=copy.copy(content)
    encountered_ids=set()
    for match_data in matches:
        if match_data[4]!=0 and is_stderr+1!=match_data[4]: continue # check stdout/stderr constraint
        if match_data[5] in encountered_ids: continue # check uuid
        else: encountered_ids.add(match_data[5])
        # Check strictness
        if target_command!=None and match_data[7]!=None and \
            _check_strictness(match_data[7], match_data[8], \
            os.path.basename(target_command.split()[0])+(" "+_globalvar.splitarray_to_string(target_command.split()[1:]) if len(target_command.split())>1 else ''))==False: continue
        if match_data[6]==True: # Foreground only
            if pids[0]!=pids[1]: continue
        matched=False
        if match_data[2]==True: # is regex 
            try: 
                ret_val: tuple=re.subn(match_data[0], match_data[1], content_str.decode('utf-8'))
                matched=ret_val[1]>0
                content_str=bytes(ret_val[0], 'utf-8')
            except UnicodeDecodeError: 
                ret_val: tuple=re.subn(bytes(match_data[0],'utf-8'), bytes(match_data[1], 'utf-8'), content_str)
                matched=ret_val[1]>0
                content_str=ret_val[0]
        else: # is string
            try: 
                matched=match_data[0] in content_str.decode('utf-8')
                content_str=bytes(content_str.decode('utf-8').replace(match_data[0], match_data[1]), 'utf-8')
            except UnicodeDecodeError: 
                matched=bytes(match_data[0], 'utf-8') in content_str
                content_str=content_str.replace(bytes(match_data[0],'utf-8'), bytes(match_data[1],'utf-8'))
        if match_data[3]==True and matched: # endmatchhere is set
            break
    return content_str
