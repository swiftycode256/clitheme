import sqlite3
from typing import Optional
try: from .. import _globalvar
except ImportError: import _globalvar

connection=sqlite3.connect(_globalvar.clitheme_root_data_path+"/"+_globalvar.db_filename)
cursor=connection.cursor()
def init_db():
    global connection, cursor
    # create the table
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_globalvar.db_data_tablename} ( \
                    match_pattern TEXT PRIMARY KEY, \
                    substitute_pattern TEXT NOT NULL \
                    );")
    # this table stores the effective commands for each match pattern 
    # Usage: find values based on "command"; obtain substitute pattern from main table using parent_match_pattern of each value
    cursor.execute("PRAGMA foreign_keys=ON;") # enable foreign keys support (in case not enabled by default)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_globalvar.db_data_tablename}_effective_commands ( \
                    command TEXT NOT NULL, \
                    parent_match_pattern TEXT NOT NULL, \
                    FOREIGN KEY (parent_match_pattern) \
                        REFERENCES {_globalvar.db_data_tablename} (match_pattern) \
                            ON UPDATE CASCADE \
                            ON DELETE CASCADE \
                    );")
    connection.commit()

def add_subst_entry(match_pattern: str, substitute_pattern: str, effective_commands: list[str]):
    global cursor
    # remove any existing values with the match_pattern, if any
    if len(cursor.execute(f"SELECT * FROM {_globalvar.db_data_tablename} WHERE match_pattern=?;", (match_pattern,)).fetchall())>0:
        # TODO: print warning message
        cursor.execute(f"DELETE FROM {_globalvar.db_data_tablename} WHERE match_pattern=?;", (match_pattern,))
    # insert the entry into the main table
    cursor.execute(f"INSERT INTO {_globalvar.db_data_tablename} (match_pattern, substitute_pattern) VALUES (?, ?);", (match_pattern, substitute_pattern))
    # update effective commands table
    for cmd in effective_commands:
        cursor.execute(f"INSERT INTO {_globalvar.db_data_tablename}_effective_commands (command, parent_match_pattern) VALUES (?, ?);", (cmd, match_pattern))
    connection.commit()

def match_content(content: str, command: Optional[str]=None):
    pass # TODO