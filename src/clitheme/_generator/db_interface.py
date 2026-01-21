# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import sqlite3
import re
import uuid
import gc
from typing import Optional, List, Dict, NamedTuple, Callable, Union
from .. import _globalvar, _frontend_internal as frontend

connection: Optional[sqlite3.Connection]=None
__db_path__=f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"
db_path=__db_path__
debug_mode=False

class need_db_regenerate(Exception): pass
class bad_pattern(Exception): pass
class db_not_found(Exception): pass

class Item(NamedTuple):
    match_pattern: str
    match_is_multiline: bool
    substitute_pattern: str
    is_regex: bool

    effective_locale: Optional[str]
    effective_command: Optional[str]
    command_match_strictness: int # 0: contains all phrases, 1: starts with, 2: equal to
    command_is_regex: bool

    foreground_only: bool
    end_match_here: bool
    stdout_stderr_only: int # 0: None; 1: stdout; 2: stderr

    unique_id: str
    file_id: str

def init_db(file_path: str):
    assert not os.path.exists(file_path), "Database file already exists"
    global connection, db_path
    db_path=file_path
    close_db() # Close previous connection
    connection=sqlite3.connect(file_path)
    # Create main table
    fields=[]
    for name, kind in Item.__annotations__.items():
        # Determine field type
        if kind==str: field_type="TEXT NOT NULL"
        elif kind in (int, bool): field_type="INTEGER NOT NULL"
        elif kind==Optional[str]: field_type="TEXT"
        else: raise AssertionError(f"Unsupported type {kind}")
        # Convert entry to SQL statement
        fields.append(' '.join([name, field_type]))
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename} ({','.join(fields)});")
    # Store version information
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename}_version (value INTEGER NOT NULL);")
    connection.execute(f"INSERT INTO {_globalvar.db_data_tablename}_version (value) VALUES (?)", (_globalvar.db_version,)) 
    connection.commit()
def connect_db(path: Optional[str]=None):
    global db_path
    if path==None: path=db_path
    else: db_path=path # Update db_path variable
    if not os.path.exists(db_path):
        raise db_not_found("No theme set or theme does not contain substrules")
    global connection
    close_db() # Close previous connection
    connection=sqlite3.connect(db_path)
    # check db version
    try:
        version=int(connection.execute(f"SELECT value FROM {_globalvar.db_data_tablename}_version").fetchone()[0])
        assert version==_globalvar.db_version
    except: raise need_db_regenerate
def close_db():
    global connection
    if connection!=None:
        connection.commit()
        connection.close()
        connection=None

def add_subst_entry(
    match_pattern: str,
    substitute_pattern: str,
    effective_commands: Optional[list],
    command_match_strictness: int,
    command_is_regex: bool,
    effective_locale: Optional[str],
    is_regex: bool,
    match_is_multiline: bool,
    end_match_here: bool,
    stdout_stderr_matchoption: int,
    foreground_only: bool,
    unique_id: uuid.UUID,
    file_id: uuid.UUID,
    line_number_debug: str,
    warning_handler: Callable[[str], None],
    warning_handler_fd: frontend.FetchDescriptor
):
    assert connection!=None, "No active database connection"
    cmdlist: List[Optional[str]]=[]

    try: re.compile(match_pattern)
    except: raise AssertionError("Uncaught bad match pattern")
    if is_regex:
        try: re.sub(match_pattern, substitute_pattern, "") # test if patterns are valid
        except: raise bad_pattern(str(sys.exc_info()[1]))

    # handle condition where no effective_locale is specified ("default")
    locale_condition="effective_locale=?" if effective_locale!=None else "typeof(effective_locale)=typeof(?)"
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
            warning_handler(warning_handler_fd.feof("repeated-substrules-warn", "Line {num}: Repeated substrules entry, overwriting", num=line_number_debug))
            connection.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE {match_condition};", match_params)
        # insert the entry into the main table
        item_tuple=Item(
            match_pattern=match_pattern,
            substitute_pattern=substitute_pattern,
            is_regex=is_regex,
            match_is_multiline=match_is_multiline,
            effective_command=cmd,
            command_match_strictness=command_match_strictness,
            command_is_regex=command_is_regex,
            end_match_here=end_match_here,
            effective_locale=effective_locale,
            stdout_stderr_only=stdout_stderr_matchoption,
            unique_id=str(unique_id),
            foreground_only=foreground_only,
            file_id=str(file_id)
        )
        connection.execute(f"INSERT INTO {_globalvar.db_data_tablename} ({','.join(item_tuple._fields)}) VALUES ({','.join('?'*len(item_tuple))});", item_tuple)
        # --Don't forget to call connection.commit with finished!--

## Database fetching and caching

_db_last_state: Optional[float]=None
_substrules_cache: Dict[Optional[str],List[Item]]={}

def _is_db_updated() -> bool:
    global _db_last_state
    try:
        # Check modification time
        cur_state=os.stat(db_path).st_mtime
    except FileNotFoundError:
        cur_state=None

    if cur_state!=_db_last_state:
        _db_last_state=cur_state
        return True
    else: return False

def fetch_substrules(command: Optional[str]) -> List[Item]:
    global _substrules_cache
    updated=_is_db_updated()
    if _db_last_state==None: _substrules_cache[command]=[]
    elif updated or _substrules_cache.get(command)==None:
        if updated:
            _substrules_cache.clear()
            gc.collect() # Reduce memory leak
        try: connect_db() # Connect database
        except need_db_regenerate: _substrules_cache[command]=[]
        else: _substrules_cache[command]=_get_matches(command)
        finally: 
            if connection!=None: close_db() # Close the file
    return _substrules_cache[command]

def _get_matches(command: Optional[str]) -> List[Item]:
    assert connection!=None, "No active database connection"
    # get locales
    locales=_globalvar.get_locale()
    # get all unique entry IDs
    entry_ids=connection.execute(f"SELECT DISTINCT unique_id FROM {_globalvar.db_data_tablename}").fetchall()
    # for each entry, attempt to fetch in locale order and then `default` locale
    match_items=[]
    for eid in entry_ids:
        fetched=False
        for locale in locales+[None]:
            assert fetched==False, "Additional locales should not be fetched"
            locale_condition="effective_locale=?" if locale!=None else "typeof(effective_locale)=typeof(?)"
            fetches=[
                Item(*data) for data in \
                    connection.execute(f"SELECT {','.join(Item._fields)} FROM {_globalvar.db_data_tablename} WHERE unique_id=? AND {locale_condition};", (eid[0], locale)).fetchall()
            ]
            if len(fetches)>0:
                for match_item in fetches:
                    # Filter based on command condition
                    if command!=None and match_item.effective_command!=None and \
                    check_command(
                        match_item.effective_command,
                        match_item.command_match_strictness,
                        command,
                        match_item.command_is_regex
                    )==False: continue
                    match_items.append(match_item)
                fetched=True
                break # Don't need to fetch additional locales
    return match_items

## Output processing and matching

def check_command(match_cmd: str, strictness: int, target_command: str, is_regex: bool) -> bool:
    def process_smartcmdmatch_phrases(match_cmd: str) -> List[str]:
        match_cmd_phrases=[]
        for p in range(len(match_cmd.split())):
            ph=match_cmd.split()[p]
            results=re.search(r"^-([^-]+)$",ph)
            if p>0 and results!=None:
                for character in results.groups()[0]: match_cmd_phrases.append("-"+character)
            else: match_cmd_phrases.append(ph)
        return match_cmd_phrases

    first_phrase=target_command.split()[0]
    valid_first_phrases=(
        first_phrase,
        os.path.basename(first_phrase),
        re.sub(r"(\.exe|\.com|\.ps1|\.bat|\.sh)$",'',os.path.basename(first_phrase)),
    )
    if is_regex:
        # Match start of target command
        for fp in valid_first_phrases:
            if re.match(f"^{match_cmd}", ' '.join([fp]+target_command.split()[1:]))!=None:
                return True
        return False
    else:
        # check starting phrase
        if not match_cmd.split()[0] in valid_first_phrases: return False

        # in following checks, first phrase is excluded as it's already checked
        if strictness==1: # must start with pattern in terms of space-separated phrases
            return len(match_cmd.split())<=len(target_command.split()) and target_command.split()[1:len(match_cmd.split())]==match_cmd.split()[1:]
        elif strictness==2: # must equal to pattern
            process=lambda cmd: ' '.join(cmd[1:])
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
