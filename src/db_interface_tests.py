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
               ("rm: <no filename>: Permission denied", "rm -rf"), # test exactcmdmatch (substitution rule containing this option should be prioritized over previous rules)
               ("example_app: using recursive directories", "example_app -rlc"), # test smartcmdmatch
               ("example_app: using list options", "example_app -rlc"), # test smartcmdmatch
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
            locale:zh_CN rm 说：缺少参数和选项 (>﹏<)
        [/substitute_string]
        [substitute_string] type rm --help for more information
            locale:default For more information, use rm --help (｡ì _ í｡)
            locale:zh_CN 关于更多信息，请使用rm --help (｡ì _ í｡)
        [/substitute_string]

    [filter_commands]
        rm -rf
        cat
        cd
        ls
    [/filter_commands]
        [substitute_regex] (?P<shell>.+): (?P<filename>.+): Permission denied
            locale:default \g<shell> says: Access denied to \g<filename>! ಥ_ಥ
            locale:zh_CN \g<shell> 说：文件"\g<filename>"拒绝访问！ಥ_ಥ
        [/substitute_regex]

    filter_command ls
        # testing repeated entry detection
        [substitute_regex] (?P<shell>.+): unrecognized option '(?P<opt>.+)'
            locale:default wef
        [/substitute_regex]
        [substitute_regex] (?P<shell>.+): unrecognized option '(?P<opt>.+)'
            locale:default \g<shell> says: option "\g<opt>" not known! (ToT)/~~~
            locale:zh_CN \g<shell> 说：未知选项"\g<opt>"！(ToT)/~~~
        [/substitute_regex]
    unset_filter_command

    # global substitutions
    [substitute_regex] ^Warning:( )
        locale:default o(≧v≦)o Note:\g<1>
        locale:zh_CN o(≧v≦)o 提示：\g<1>
    [/substitute_regex]
    [substitute_regex] ^Error:( )
        locale:default (ToT)/~~~ Error:\g<1>
        locale:zh_CN (ToT)/~~~ 错误：
    [/substitute_regex]
    [substitute_regex] invaild input( )*$
        locale:default input is invaild! ಥ_ಥ
        locale:zh_CN 无效输入！ಥ_ಥ
    [/substitute_regex]

    set_options strictcmdmatch
    filter_command example_app install-stuff
        [substitute_string] Error: sample message
            locale:default Error: sample message! (>﹏<)
            locale:zh_CN 错误：样例提示！(>﹏<)
        [/substitute_string] endmatchhere

    set_options exactcmdmatch
    filter_command rm -rf
        [substitute_regex] (?P<shell>.+): (?P<filename>.+): Permission denied
            locale:default \g<shell> says: Missing argument for operation! ಥ_ಥ
            locale:zh_CN \g<shell> 说：缺少操作参数！ಥ_ಥ
        [/substitute_regex]
    
    set_options noexactcmdmatch
    filter_command example_app
        [substitute_string] example_app:
            locale:default o(≧v≦)o example_app says:
            locale:zh_CN o(≧v≦)o example_app 说：
        [/substitute_string]
    set_options smartcmdmatch
    filter_command example_app -r
        [substitute_string] using recursive directories
            locale:default using recursive directories! (｡ì _ í｡)
            locale:zh_CN 正在使用子路径！(｡ì _ í｡)
        [/substitute_string]
    filter_command example_app -l
        [substitute_string] using list options
            locale:default using list options! (⊙ω⊙)
            locale:zh_CN 正在使用列表选项！(⊙ω⊙)
        [/substitute_string]
    set_options nosmartcmdmatch
{/substrules_section}
"""

_generator.generate_data_hierarchy(substrules_file)
db_interface.connection=db_interface.sqlite3.connect(_generator.path+"/"+_globalvar.db_filename)

print("Successfully recorded data\nTesting sample outputs: ")
for inp in sample_inputs:
    print(db_interface.match_content(bytes(inp[0],'utf-8'),command=inp[1]).decode('utf-8'))
