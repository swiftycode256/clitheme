from clitheme._generator import db_interface

# sample input for testing
sample_inputs=[("rm: missing operand", "rm"),
               ("type rm --help for more information", "rm"),
               ("rm: /etc/folder: Permission denied", "rm -rf /etc/folder"),
               ("cat: /dev/mem: Permission denied","cat /dev/mem"),
               ("bash: /etc/secret: Permission denied","cd /etc/secret"),
               ("ls: /etc/secret: Permission denied","ls /etc/secret"),
               ("ls: /etc/secret: Permission denied","wef ls /etc/secret"), # test first phrase detection
               ("ls: unrecognized option '--help'", "ls --help"),
               ("Warning: invaild input", "input anything"),
               ("Error: invaild input   ","input anything"), # test extra spaces
]
# substitute patterns
subst_patterns=[("rm: missing operand", "rm says: missing arguments and options (>﹏<)", False, ["rm"]),
                ("type rm --help for more information", "For more information, use rm --help (｡ì _ í｡)", False, ["rm"]),
                (r"(?P<shell>.+): (?P<filename>.+): Permission denied",r"""\g<shell> says: Access denied to \g<filename>! ಥ_ಥ""",True, ["rm", "cat", "cd", "ls"]),
                (r"(?P<shell>.+): unrecognized option '(?P<opt>.+)'",r"""wef""",True, ["ls"]), # testing repeated entry detection
                (r"(?P<shell>.+): unrecognized option '(?P<opt>.+)'",r"""\g<shell> says: option '\g<opt>' not known! (ToT)/~~~'""",True, ["ls"]),
                (r"^Warning:( )", r"o(≧v≦)o Note:\g<1>",True , None),
                (r"^Error:( )", r"(ToT)/~~~ Error:\g<1>",True, None),
                (r"invaild input( ){0,}$", r"input is invaild! ಥ_ಥ", True, None)]

db_interface.init_db(":memory:")
# record substitute patterns
for dat in subst_patterns: db_interface.add_subst_entry(match_pattern=dat[0], substitute_pattern=dat[1], effective_commands=dat[3], is_regex=dat[2])
print("Successfully recorded data\nTesting sample outputs: ")
for inp in sample_inputs:
    print(db_interface.match_content(bytes(inp[0],'utf-8'),command=inp[1]).decode('utf-8'))
