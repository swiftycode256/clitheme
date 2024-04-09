from clitheme._generator import db_interface

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
# (match_pattern, substitute_pattern, is_regex, effective_commands, command_match_strictness, end_match_here)
subst_patterns=[("rm: missing operand", "rm says: missing arguments and options (>﹏<)", False, ["rm"], 0, False),
                ("type rm --help for more information", "For more information, use rm --help (｡ì _ í｡)", False, ["rm"], 0, False),
                (r"(?P<shell>.+): (?P<filename>.+): Permission denied",r"""\g<shell> says: Access denied to \g<filename>! ಥ_ಥ""",True, ["rm -rf", "cat", "cd", "ls"], 0, False),
                (r"(?P<shell>.+): unrecognized option '(?P<opt>.+)'",r"""wef""",True, ["ls"], 0, False), # testing repeated entry detection
                (r"(?P<shell>.+): unrecognized option '(?P<opt>.+)'",r"""\g<shell> says: option '\g<opt>' not known! (ToT)/~~~'""",True, ["ls"], 0, False),
                (r"^Warning:( )", r"o(≧v≦)o Note:\g<1>",True , None, 0, False),
                (r"^Error:( )", r"(ToT)/~~~ Error:\g<1>",True, None, 0, False),
                (r"invaild input( ){0,}$", r"input is invaild! ಥ_ಥ", True, None, 0, False),
                ("Error: sample message", "Error: sample message! (>﹏<)", False, ["example_app install-stuff"], 1, True),
                (r"(?P<shell>.+): (?P<filename>.+): Permission denied",r"""\g<shell> says: Missing argument for operation! ಥ_ಥ""",True, ["rm -rf"], 2, False),
]

db_interface.init_db(":memory:")
# record substitute patterns
for dat in subst_patterns: db_interface.add_subst_entry(match_pattern=dat[0], substitute_pattern=dat[1], effective_commands=dat[3], is_regex=dat[2], command_match_strictness=dat[4], end_match_here=dat[5])
print("Successfully recorded data\nTesting sample outputs: ")
for inp in sample_inputs:
    print(db_interface.match_content(bytes(inp[0],'utf-8'),command=inp[1]).decode('utf-8'))
