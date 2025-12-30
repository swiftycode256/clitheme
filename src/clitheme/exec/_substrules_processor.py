# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Handler for applying substrules onto output (internal module)
"""

import copy
import re
import os
import signal
from typing import Optional, List, Set, Tuple
from .._generator import db_interface
from .. import _globalvar

def match_content(content: bytes, command: Optional[str]=None, is_stderr: bool=False, pids: Tuple[int,int]=(-1,-1)) -> Tuple[bytes, Set[int]]:
    # pids: (main_pid, current_tcpgrp)

    content_str=copy.copy(content)
    # Convert to str if possible
    try: content_str=content_str.decode('utf-8')
    except: pass
    assert len(content_str)>0, "Empty content string"

    substrules=db_interface.fetch_substrules(command)

    encountered_ids=set()
    # endmatchhere checking algorithm:
    # - Keep track of condition mapping with same length as content
    # - After each substitution, mark affected range in condition map and update length
    # - When file ID changes, reset condition mapping (re-occurring ID should never happen)
    # -> Check if affected *lines* in the condition map are marked
    if type(content_str)==bytes:
        line_match=_globalvar.line_match_bytes
    else: line_match=_globalvar.line_match
    encountered_files=set()
    last_file_id=''
    # > \x00: not matched; \x01: matched; \x02: end match here
    condition_map=bytearray()
    def init_condition_map():
        nonlocal condition_map
        condition_map=bytearray(len(content_str))
    init_condition_map()

    if os.name=="posix":
        # Set timeout handler
        def timeout(sig_num, frame): raise TimeoutError
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, _globalvar.output_subst_timeout)
    for rule in substrules:
        # region: Condition checking
        if rule.unique_id in encountered_ids: continue
        if rule.stdout_stderr_only!=0 and (is_stderr==True)+1!=rule.stdout_stderr_only: continue
        if command!=None and rule.effective_command!=None and \
            db_interface.check_command(
                rule.effective_command,
                rule.command_match_strictness,
                command,
                rule.command_is_regex
            )==False: continue
        if rule.foreground_only==True and pids[0]!=pids[1]: continue
        # Reset endmatchhere condition map for new files
        if rule.file_id!=last_file_id:
            assert rule.file_id not in encountered_files, "Revisited file ID"
            encountered_files.add(rule.file_id)
            last_file_id=rule.file_id
            init_condition_map()
        # endregion

        # region: Match operation
        match_pattern=rule.match_pattern if rule.is_regex else re.escape(rule.match_pattern)
        # Replace newlines in multiline match pattern to match all possible newlines
        match_pattern=re.sub(r'\n' if rule.is_regex else r'\\\n', # '\n' is escaped in re.escape
               rf"(?:{'|'.join(s.decode('utf-8') for s in _globalvar.newlines)})",
               match_pattern)
        if type(content_str)==bytes: match_pattern=match_pattern.encode('utf-8')
        sub_pattern=rule.substitute_pattern

        if rule.match_is_multiline:
            # Search in entire block
            line_lengths=[len(content_str)]
        else:
            # Search in individual lines
            line_lengths=[len(m.group()) for m in re.finditer(line_match, content_str)] # type: ignore
            # The EOL delimiter might match empty string at end of line
            if line_lengths[-1]==0: line_lengths.pop(-1)
        new_condition_map=condition_map
        new_condition_map_offset=0
        new_content=content_str
        matched=False
        offset=0
        cur_start=0
        for length in line_lengths:
            assert cur_start==0 or content_str[cur_start-1:cur_start] in \
                _globalvar.newlines+tuple(s.decode('utf-8') for s in _globalvar.newlines), \
                f"Previous character is not a newline: {repr(content_str[cur_start-1:cur_start])}"
            if cur_start>0:
                # Replace previous newline character with '\n' to ensure re.MULTILINE works
                match_str=content_str[:cur_start-1]+(b'\n' if type(content_str)==bytes else '\n')+content_str[cur_start:] # type: ignore
            else: match_str=content_str
            assert len(match_str)==len(content_str), \
                f"Length mismatch: {len(match_str)}!={len(content_str)}"
            # Perform sub on each line
            obj_list: List[re.Match]=\
                list(re.compile(match_pattern, flags=re.MULTILINE) \
                    .finditer(match_str, cur_start, cur_start+length)) # type: ignore
            for match in obj_list:
                # region: Check endmatchhere
                # Determine start range: seek backward before newline is reached
                assert len(content_str)==len(condition_map)
                line_start=match.start()
                for pos in range(match.start()-1, 0-1, -1):
                    ch=content_str[pos]
                    if ch not in (0,1) and content_str[pos:pos+2] not in (b'\r\n','\r\n'): # Newline character
                        break
                    else: line_start=pos
                # Determine end range: seek forward after newline is reached
                line_end=match.end()
                for pos in range(match.end(), len(content_str)+1):
                    ch=content_str[pos-1]
                    line_end=pos
                    if ch not in (0,1): # Newline character
                        if content_str[pos-1:pos-1+2] in (b'\r\n', '\r\n'):
                            line_end=pos+1
                        break
                if re.compile(b'\x02').search(condition_map, line_start, line_end)!=None:
                    continue # Skip if marked sections found
                else: matched=True
                # endregion

                if type(content_str)==str: sub=sub_pattern
                elif type(content_str)==bytes: sub=sub_pattern.encode('utf-8')
                else: raise AssertionError
                # Perform substitution
                if rule.is_regex: new_str=match.expand(sub)
                else: new_str=sub
                new_content=new_content[:match.start()+offset]+new_str+new_content[match.end()+offset:] # type: ignore
                offset+=len(new_str)-(match.end()-match.start())
                
                # region: Update new condition map
                # \x02 and \x01 for T/F endmatchhere condition
                sub=bytearray([(rule.end_match_here==True)+1]*len(new_str)) # Sub pattern length
                new_condition_map=\
                    new_condition_map[:match.start()+new_condition_map_offset] \
                    +sub \
                    +new_condition_map[match.end()+new_condition_map_offset:]
                new_condition_map_offset+=len(sub)-(match.end()-match.start())
                # endregion
            cur_start+=length
        assert len(new_condition_map)==len(new_content), \
            f"Length mismatch: {len(new_condition_map)}!={len(new_content)}"
        content_str=new_content
        condition_map=new_condition_map
        if matched: encountered_ids.add(rule.unique_id)
    # endregion
    if os.name=="posix":
        # Remove timeout trigger
        signal.setitimer(signal.ITIMER_REAL, 0)
    # region: Check modified lines
    line_lengths=[len(m.group()) for m in re.finditer(line_match, content_str)] # type: ignore
    changed_line_indices=set()
    cur_start=0
    for x in range(len(line_lengths)):
        length=line_lengths[x]
        if re.compile(b'\x01|\x02').search(condition_map, cur_start, cur_start+length)!=None:
            changed_line_indices.add(x)
        cur_start+=length
    # endregion
    
    if type(content_str)==str:
        return (bytes(content_str, 'utf-8'), changed_line_indices)
    elif type(content_str)==bytes:
        return (content_str, changed_line_indices)
    else: raise AssertionError
