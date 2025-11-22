# Copyright © 2023-2025 swiftycode

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
import gc
from typing import Optional, List, Tuple, Dict, NamedTuple
from .. import _globalvar, frontend

# spell-checker:ignore matchoption cmdlist exactmatch rowid pids tcpgrp nolocale

connection=sqlite3.connect(":memory:") # placeholder
db_path=""
debug_mode=False
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")

class need_db_regenerate(Exception): pass
class bad_pattern(Exception): pass
class db_not_found(Exception): pass

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
                    file_id TEXT NOT NULL, \
                    effective_command TEXT, \
                    command_match_strictness INTEGER NOT NULL, \
                    command_is_regex INTEGER NOT NULL, \
                    effective_locale TEXT, \
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
    try:
        version=int(connection.execute(f"SELECT value FROM {_globalvar.db_data_tablename}_version").fetchone()[0])
        assert version==_globalvar.db_version
    except: raise need_db_regenerate

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: Optional[list], command_match_strictness: int=0, command_is_regex: bool=False, effective_locale: Optional[str]=None, is_regex: bool=True, end_match_here: bool=False, stdout_stderr_matchoption: int=0, foreground_only: bool=False, unique_id: uuid.UUID=uuid.UUID(int=0), file_id: uuid.UUID=uuid.UUID(int=0), line_number_debug: str="-1"):
    if unique_id==uuid.UUID(int=0): unique_id=uuid.uuid4()
    cmdlist: List[Optional[str]]=[]
    try: re.sub(match_pattern, substitute_pattern, "") # test if patterns are valid
    except: raise bad_pattern(str(sys.exc_info()[1]))
    # handle condition where no effective_locale is specified ("default")
    locale_condition="effective_locale=?" if effective_locale!=None else "typeof(effective_locale)=typeof(?)"
    insert_values=["match_pattern", "substitute_pattern", "is_regex", "effective_command", "command_match_strictness", "command_is_regex", "end_match_here", "effective_locale", "stdout_stderr_only", "unique_id", "foreground_only", "file_id"]
    if effective_commands!=None and len(effective_commands)>0: 
        for cmd in effective_commands:
            # remove extra spaces in the command
            cmdlist.append(re.sub(r" {2,}", " ", cmd).strip())
    else:
        cmdlist=[None]
    for cmd in cmdlist:
        # remove any existing values with the same match_pattern and effective_command
        strictness_condition="1" # Nothing for now
        cmd_condition='effective_command=?' if cmd!=None else 'typeof(effective_command)=typeof(?)'
        match_condition=f"match_pattern=? AND {cmd_condition} AND command_is_regex=? AND {strictness_condition} AND {locale_condition} AND stdout_stderr_only=? AND is_regex=?"
        match_params=(match_pattern, cmd, command_is_regex, effective_locale, stdout_stderr_matchoption, is_regex)
        if len(connection.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params).fetchall())>0:
            _handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(insert_values)}) VALUES ({','.join('?'*len(insert_values))});", (match_pattern, substitute_pattern, is_regex, cmd, command_match_strictness, command_is_regex, end_match_here, effective_locale, stdout_stderr_matchoption, str(unique_id), foreground_only, str(file_id)))
    connection.commit()

## Database fetch caching
class _Item(NamedTuple):
    match_pattern: str
    substitute_pattern: str
    is_regex: bool
    unique_id: str
    file_id: str
    effective_command: str
    command_match_strictness: int
    command_is_regex: bool
    effective_locale: str
    foreground_only: bool
    end_match_here: bool
    stdout_stderr_only: int # 0: None; 1: stdout; 2: stderr
    rowid: str

_db_last_state: Optional[float]=None
_matches_cache: Dict[Optional[str],List[_Item]]={}

def _is_db_updated() -> bool:
    global _db_last_state
    cur_state: Optional[float]
    try:
        # Check modification time
        cur_state=os.stat(db_path).st_mtime
    except FileNotFoundError: cur_state=None
    updated=False
    if cur_state!=_db_last_state:
        updated=True
        _db_last_state=cur_state
    return updated

def _fetch_matches(command: Optional[str]) -> List[_Item]:
    global _matches_cache
    updated=_is_db_updated()
    if _db_last_state==None: raise db_not_found("file at db_path does not exist")
    if updated or _matches_cache.get(command)==None:
        if updated:
            _matches_cache.clear()
            gc.collect() # Reduce memory leak
        _matches_cache[command]=_get_matches(command)
    return _matches_cache[command]

## Output processing and matching

def _get_matches(command: Optional[str]) -> List[_Item]:
    matches=[]
    fetch_items=_Item._fields
    # get locales
    locales=_globalvar.get_locale()
    # get all unique entry IDs
    entry_ids=connection.execute(f"SELECT DISTINCT unique_id FROM {_globalvar.db_data_tablename}").fetchall()
    # for each entry, fetch in locale order and then `default` locale
    for eid in entry_ids:
        for locale in locales+[None]:
            locale_condition="effective_locale=?" if locale!=None else "typeof(effective_locale)=typeof(?)"
            matches+=connection.execute(f"SELECT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE unique_id=? AND {locale_condition};", (eid[0], locale)).fetchall()
    match_items=[]
    for item in matches:
        match_items.append(_Item(*item))
    return match_items

def _check_command(match_cmd: str, strictness: int, target_command: str, is_regex: bool) -> bool:
    def process_smartcmdmatch_phrases(match_cmd: str) -> List[str]:
        match_cmd_phrases=[]
        for p in range(len(match_cmd.split())):
            ph=match_cmd.split()[p]
            results=re.search(r"^-([^-]+)$",ph)
            if p>0 and results!=None:
                for character in results.groups()[0]: match_cmd_phrases.append("-"+character)
            else: match_cmd_phrases.append(ph)
        return match_cmd_phrases
    if is_regex:
        # Match start of target command
        return re.match(f"^{match_cmd}", target_command)!=None
    else:
        # check starting phrase
        first_phrase=target_command.split()[0]
        if not match_cmd.split()[0] in (
            first_phrase,
            os.path.basename(first_phrase),
            re.sub(r"(\.exe|\.com|\.ps1|\.bat)$",'',os.path.basename(first_phrase)),
        ): return False

        # in following checks, first phrase is excluded as it's already checked
        if strictness==1: # must start with pattern in terms of space-separated phrases
            return len(match_cmd.split())<=len(target_command.split()) and target_command.split()[1:len(match_cmd.split())]==match_cmd.split()[1:]
        elif strictness==2: # must equal to pattern
            process=lambda cmd: _globalvar.splitarray_to_string(cmd[1:])
            return process(match_cmd)==process(target_command)
        elif strictness==-1: # smartcmdmatch: split phrases starting with one '-' and split them. Then, perform strictness==0 check
            # process both phrases
            match_cmd_phrases=process_smartcmdmatch_phrases(match_cmd)
            command_phrases=process_smartcmdmatch_phrases(target_command)
            for phrase in match_cmd_phrases[1:]:
                if phrase not in command_phrases[1:]: return False
        else: # strictness==0; must contain all phrases in pattern
            for phrase in match_cmd.split()[1:]:
                if phrase not in target_command.split()[1:]: return False
        return True

def match_content(content: bytes, command: Optional[str]=None, is_stderr: bool=False, pids: Tuple[int,int]=(-1,-1)) -> bytes:
    # pids: (main_pid, current_tcpgrp)

    matches=_fetch_matches(command)
    content_str=_handle_subst(matches, content, is_stderr, pids, command)
    return content_str

# timeout value for each match operation
match_timeout=_globalvar.output_subst_timeout

def _handle_subst(matches: List[_Item], content: bytes, is_stderr: bool, pids: Tuple[int,int], target_command: Optional[str]) -> bytes:
    content_str=copy.copy(content)
    encountered_ids=set()
    skipped_files=set() # File ids skipped with endmatchhere option
    for match_data in matches:
        # check stdout/stderr constraint
        if match_data.stdout_stderr_only!=0 and is_stderr+1!=match_data.stdout_stderr_only: continue
        if match_data.unique_id in encountered_ids: continue
        if match_data.file_id in skipped_files: continue 
        # Check command
        if target_command!=None and match_data.effective_command!=None and \
            _check_command(
                match_data.effective_command,
                match_data.command_match_strictness,
                target_command,
                match_data.command_is_regex
            )==False: continue
        if match_data.foreground_only==True: # Foreground only
            if pids[0]!=pids[1]: continue
        matched=False
        if match_data.is_regex==True: # is regex 
            try: 
                ret_val: tuple=re.subn(match_data.match_pattern, match_data.substitute_pattern, content_str.decode('utf-8'))
                matched=ret_val[1]>0
                content_str=bytes(ret_val[0], 'utf-8')
            except UnicodeDecodeError: 
                ret_val: tuple=re.subn(bytes(match_data.match_pattern,'utf-8'), bytes(match_data.substitute_pattern, 'utf-8'), content_str)
                matched=ret_val[1]>0
                content_str=ret_val[0]
        else: # is string
            try: 
                matched=match_data.match_pattern in content_str.decode('utf-8')
                content_str=bytes(content_str.decode('utf-8').replace(match_data.match_pattern, match_data.substitute_pattern), 'utf-8')
            except UnicodeDecodeError: 
                matched=bytes(match_data.match_pattern, 'utf-8') in content_str
                content_str=content_str.replace(bytes(match_data.match_pattern,'utf-8'), bytes(match_data.substitute_pattern,'utf-8'))
        if matched:
            encountered_ids.add(match_data.unique_id)
            if match_data.end_match_here==True: # endmatchhere is set
                skipped_files.add(match_data.file_id)
    return content_str
