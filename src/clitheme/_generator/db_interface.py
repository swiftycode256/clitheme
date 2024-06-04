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
import time
import signal
import multiprocessing, concurrent.futures
import queue
from typing import Optional
from .. import _globalvar, frontend

# spell-checker:ignore matchoption cmdlist exactmatch rowid

connection=sqlite3.connect(":memory:") # placeholder
db_path=""
debug_mode=False
_globalvar.handle_set_themedef(frontend, "db_interface")
fd=frontend.FetchDescriptor(domain_name="swiftycode", app_name="clitheme", subsections="generator")
try: multiprocessing.set_start_method('fork', force=True)
except: pass

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
                    end_match_here INTEGER NOT NULL, \
                    stdout_stderr_only INTEGER NOT NULL \
                    );")
    connection.execute(f"CREATE TABLE {_globalvar.db_data_tablename}_version (value INTEGER NOT NULL);")
    connection.execute(f"INSERT INTO {_globalvar.db_data_tablename}_version (value) VALUES (?)", (_globalvar.db_version,)) 
    connection.commit()
def connect_db(path: str=f"{_globalvar.clitheme_root_data_path}/{_globalvar.db_filename}"):
    if not os.path.exists(path):
        raise FileNotFoundError("No theme set or theme does not contain substrules")
    global db_path
    db_path=path
    global connection
    connection=sqlite3.connect(db_path)
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
            _handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
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
            _handle_warning(fd.feof("repeated-substrules-warn", "Repeated substrules entry at line {num}, overwriting", num=line_number_debug))
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
    _connection=sqlite3.connect(db_path)
    final_cmdlist=[]
    final_cmdlist_exactmatch=[]
    if command!=None and len(command.split())>0:
        # command without paths (e.g. /usr/bin/bash -> bash)
        stripped_command=os.path.basename(command.split()[0])+" "+(_globalvar.splitarray_to_string(command.split()[1:]) if len(command.split())>1 else '')
        # obtain a list of effective_command with the same first term
        cmdlist=_connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command LIKE ? or effective_command LIKE ?;", (command.split()[0].strip()+" %", stripped_command.split()[0].strip()+" %")).fetchall()
        # also include one-phrase commands
        cmdlist+=_connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE effective_command=? or effective_command=?;", (command.split()[0].strip(),stripped_command.split()[0].strip())).fetchall()
        # sort by number of phrases (greatest to least)
        def split_len(obj: tuple) -> int: return len(obj[0].split())
        cmdlist.sort(key=split_len, reverse=True)
        # prioritize effective_command with exact match requirement
        cmdlist=_connection.execute(f"SELECT DISTINCT effective_command, command_match_strictness FROM {_globalvar.db_data_tablename} WHERE (effective_command=? OR effective_command=?) AND command_match_strictness=2", (re.sub(r" {2,}", " ", command).strip(),re.sub(r" {2,}", " ", stripped_command).strip())).fetchall()+cmdlist
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
        for target_command in [command, stripped_command]:
            for tp in cmdlist:
                match_cmd: str=tp[0].strip() # extract value from tuple
                strictness: int=tp[1] # strictness setting
                success=True
                if strictness==1: # must start with pattern in terms of space-separated phrases
                    condition=len(match_cmd.split())<len(target_command.split()) and target_command.split()[:len(match_cmd.split())]==match_cmd.split()
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
                if success:
                    # if found matching target_command
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
            fetch_data=_connection.execute(f"SELECT DISTINCT {','.join(fetch_items)} FROM {_globalvar.db_data_tablename} WHERE {filter_condition} AND effective_locale=? ORDER BY rowid;", filter_data+(this_locale,)).fetchall()
            if len(fetch_data)>0:
                matches+=fetch_data
                return
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
    global enable_multiprocessing, match_timeout
    if enable_multiprocessing:
        global _running_processes_ids
        if len(_running_processes_ids)==0:
            _init_process()
        result_id=uuid.uuid4()
        global _input_values; _input_values.put((matches, content_str, is_stderr, result_id))
        counter=0
        watchdog_timer=0
        while counter<match_timeout:
            time.sleep(0.001)
            if result_id in _return_values.keys():
                if _return_values[result_id]==None: # Processing
                    counter+=0.001
                else: 
                    content_str=_return_values[result_id]
                    del _return_values[result_id]
                    break
            else:
                # Handle cases when the data didn't get processed at all
                watchdog_timer+=0.001
                if watchdog_timer>=1.500:
                    _init_process()
                    _input_values.put((matches, content_str, is_stderr, result_id))
                    watchdog_timer=0
        else: # executed when no "break" happens
            try: del _return_values[result_id]
            except: pass
            _init_process() # restart the process
            raise TimeoutError("match operation timeout")
    else:
        content_str=_handle_subst(matches, content_str, is_stderr)
    return content_str

# --The following implementation (A) is for setting a timeout capacity on content match functions--
    # - A main loop is started for handling substitution requests and returns the corresponding content based on UUID
    # - If the main loop times out due to catastrophic backtracking or other issues, match_content terminates the loop
    # - The main loop is checked and restored (if needed) every time match_content is called, while preserving input queue and return values (resumes seamlessly)
    # ** May impact performance and is currently prone to random hangs, especially under Linux **
# --An alternative implementation (B) is available in output_handler_posix, but multithreading can't be used and doesn't work under Windows--

# Flag to determine whether implementation A is used
# If False, implementation B is used in output_handler_posix under Unix/Linux
enable_multiprocessing=False
# timeout value for each match operation
match_timeout=0.4

_manager=multiprocessing.Manager()
_process: Optional[multiprocessing.Process]=None
_input_values=multiprocessing.Queue() # (matches, content, is_stderr, uuid)
_return_values=_manager.dict() # uuid : content_str (uuid:None means processing)

_watchdog_process: Optional[multiprocessing.Process]=None
_running_processes_ids=_manager.list()

def _init_process():
    global _process, _input_values, _return_values, _watchdog_process, _running_processes_ids
    # if _process!=None and _process.is_alive(): _process.terminate()
    if _watchdog_process==None:
        _watchdog_process=multiprocessing.Process(name="process_watchdog", target=__process_watchdog, args=(_running_processes_ids,), daemon=True)
        _watchdog_process.start()
    _process=multiprocessing.Process(name="subst_content_handler", target=__process_main_loop, args=(_input_values, _return_values, _running_processes_ids), daemon=True)
    try: _process.start()
    except AssertionError: _init_process();return # handle "cannot start a process twice" error by trying again
    # _running_processes_ids.append(_process.pid)
# watchdog to terminate any processes other than the current one
def __process_watchdog(running_ids):
    while True:
        try: 
            time.sleep(0.01)
            # kill all processes except the most recently started one (last in list)
            l=running_ids[:-1]
            for pid in l:
                try: 
                    os.kill(pid, signal.SIGTERM)
                    running_ids.remove(pid)
                except: pass
        except KeyboardInterrupt: pass
def __process_main_loop(input_vals: multiprocessing.Queue, return_vals: dict, process_ids: list):
    process_ids.append(os.getpid())
    executor=concurrent.futures.ThreadPoolExecutor(max_workers=32)
    def handler():
        nonlocal return_vals, input_vals
        # the function might be called extra times if operation is queued, so a check is performed
        content: tuple
        try: content=input_vals.get_nowait()
        except queue.Empty: return
        return_vals[content[3]]=None # Processing
        return_str=_handle_subst(content[0], content[1], content[2])
        return_vals[content[3]]=return_str
    while True:
        try: time.sleep(0.001)
        except KeyboardInterrupt: pass
        try:
                executor.submit(handler)
                # handler()
        except KeyboardInterrupt: pass
        # except: break

def _handle_subst(matches: list[tuple], content: bytes, is_stderr: bool, ret: Optional[list[bytes]]=None):
    content_str=copy.copy(content)
    encountered_ids=set()
    for match_data in matches:
        if match_data[4]!=0 and is_stderr+1!=match_data[4]: continue # check stdout/stderr constraint
        if match_data[5] in encountered_ids: continue # check uuid
        else: encountered_ids.add(match_data[5])
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
    if ret!=None: ret.append(content_str)
    return content_str
