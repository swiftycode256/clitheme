from clitheme._generator import db_interface
from clitheme import _generator, _globalvar

# sample input for testing
sample_inputs=[("rm: missing operand", "rm"),
               ("type rm --help for more information", "rm"),
               ("rm: /etc/folder: Permission denied", "rm /etc/folder -rf"),
               ("rm: /etc/file: Permission denied", "rm /etc/folder"), # test multiple phrase detection (substitution should not happen)
               ("cat: /dev/mem: Permission denied","cat /dev/mem"),
               ("bash: /etc/secret: Permission denied","cd /etc/secret"),
               ("ls: /etc/secret: Permission denied","ls /etc/secret"),
               ("ls: /etc/secret: Permission denied","wef ls /etc/secret"), # test first phrase detection (substitution should not happen)
               ("ls: unrecognized option '--help'", "ls --help"),
               ("Warning: invaild input", "input anything"),
               ("Error: invaild input   ","input anything"), # test extra spaces
               ("Error: sample message", "example_app --this install-stuff"), # test strictcmdmatch (substitution should not happen)
               ("Error: sample message", "example_app install-stuff --this"), # test strictcmdmatch and endmatchhere options
               ("rm: <no filename>: Permission denied", "rm -rf") # test exactcmdmatch (substitution rule containing this option should be prioritized over previous rules)
]
# substitute patterns
substrules_file=r"""
{header_section}
    name test
{/header_section}
{substrules_section}
    filter_command rm
        [substitute_string] rm: missing operand
            locale:default rm says: missing arguments and options (>﹏<)
        [/substitute_string]
        [substitute_string] type rm --help for more information
            locale:default For more information, use rm --help (｡ì _ í｡)
        [/substitute_string]
    [filter_commands]
        rm -rf
        cat
        cd
        ls
    [/filter_commands]
        [substitute_regex] (?P<shell>.+): (?P<filename>.+): Permission denied
            locale:default \g<shell> says: Access denied to \g<filename>! ಥ_ಥ
        [/substitute_regex]
    filter_command ls
        # testing repeated entry detection
        [substitute_regex] (?P<shell>.+): unrecognized option '(?P<opt>.+)'
            locale:default wef
        [/substitute_regex]
        [substitute_regex] (?P<shell>.+): unrecognized option '(?P<opt>.+)'
            locale:default \g<shell> says: option '\g<opt>' not known! (ToT)/~~~'
        [/substitute_regex]
    unset_filter_command
    [substitute_regex] ^Warning:( )
        locale:default o(≧v≦)o Note:\g<1>
    [/substitute_regex]
    [substitute_regex] ^Error:( )
        locale:default (ToT)/~~~ Error:\g<1>
    [/substitute_regex]
    [substitute_regex] invaild input( ){0,}$
        locale:default input is invaild! ಥ_ಥ
    [/substitute_regex]
    set_options strictcmdmatch
    filter_command example_app install-stuff
        [substitute_string] Error: sample message
            locale:default Error: sample message! (>﹏<)
        [/substitute_string] endmatchhere
    set_options exactcmdmatch
    filter_command rm -rf
        [substitute_regex] (?P<shell>.+): (?P<filename>.+): Permission denied
            locale:default \g<shell> says: Missing argument for operation! ಥ_ಥ
        [/substitute_regex]
    set_options noexactcmdmatch nostrictcmdmatch
{/substrules_section}
"""

# db_interface.init_db(":memory:")
# # record substitute patterns
# for dat in subst_patterns: db_interface.add_subst_entry(match_pattern=dat[0], substitute_pattern=dat[1], effective_commands=dat[3], is_regex=dat[2], command_match_strictness=dat[4], end_match_here=dat[5])

_generator.generate_data_hierarchy(substrules_file)
db_interface.connection=db_interface.sqlite3.connect(_generator.path+"/"+_globalvar.db_filename)

print("Successfully recorded data\nTesting sample outputs: ")
for inp in sample_inputs:
    print(db_interface.match_content(bytes(inp[0],'utf-8'),command=inp[1]).decode('utf-8'))
