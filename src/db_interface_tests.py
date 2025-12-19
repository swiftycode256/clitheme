# Copyright © 2023-2025 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from clitheme._generator import db_interface
from clitheme import _generator, _globalvar
import shutil

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
               ("Warning: invalid input", "input anything"),
               ("Error: invalid input   ","input anything"), # test extra spaces
               ("Error: sample message", "example_app --this install-stuff"), # test strictcmdmatch (substitution should not happen)
               ("Error: sample message", "example_app install-stuff --this"), # test strictcmdmatch and endmatchhere options
               ("Error: sample message", "example_app install-stuff"), # test strictcmdmatch with SAME command as defined in filter
               # Test regex filters
               ("Error: sample message", "/usr/bin/app_example.exe install-stuff"), # test command basename handling in regex
               ("Error: sample message", "app --wef install"),
               ("rm: <no filename>: Operation not permitted", "rm file.ban"), # test exactcmdmatch
               ("example_app: using recursive directories", "example_app -rlc"), # test smartcmdmatch
               ("example_app: using list options", "/usr/bin/example_app.exe -rlc"), # test smartcmdmatch and command basename handling
]
expected_outputs=[
    ("rm says: missing arguments and options (>﹏<)", "rm 说：缺少参数和选项 (>﹏<)"),
    ("For more information, use rm --help (｡ì _ í｡)", "关于更多信息，请使用rm --help (｡ì _ í｡)"),
    ("rm says: Access denied to /etc/folder! ಥ_ಥ", "rm 说：文件\"/etc/folder\"拒绝访问！ಥ_ಥ"),
    ("rm: /etc/file: Permission denied",),
    ("cat says: Access denied to /dev/mem! ಥ_ಥ", "cat 说：文件\"/dev/mem\"拒绝访问！ಥ_ಥ"),
    ("bash says: Access denied to /etc/secret! ಥ_ಥ", "bash 说：文件\"/etc/secret\"拒绝访问！ಥ_ಥ"),
    ("ls says: Access denied to /etc/secret! ಥ_ಥ", "ls 说：文件\"/etc/secret\"拒绝访问！ಥ_ಥ"),
    ("ls: /etc/secret: Permission denied",),
    ("ls says: option \"--help\" not known! (ToT)/~~~", "ls 说：未知选项\"--help\"！(ToT)/~~~"),
    ("o(≧v≦)o Note: input is invalid! ಥ_ಥ", "o(≧v≦)o 提示： 无效输入！ಥ_ಥ"),
    ("(ToT)/~~~ Error: input is invalid! ಥ_ಥ", "(ToT)/~~~ 错误：无效输入！ಥ_ಥ"),
    ("(ToT)/~~~ Error: sample message", "(ToT)/~~~ 错误：sample message"),
    ("Error: \x1b[1;4msample message!\x1b[m (>﹏<)", "错误：样例提示！(>﹏<)"),
    ("Error: \x1b[1;4msample message!\x1b[m (>﹏<)", "错误：样例提示！(>﹏<)"),
    ("Error: \x1b[1;4msample message!\x1b[m (>﹏<)", "错误：样例提示！(>﹏<)"),
    ("Error: \x1b[1;4msample message!\x1b[m (>﹏<)", "错误：样例提示！(>﹏<)"),
    ("rm says: \x1b[1;4mOperation not permitted!\x1b[0m ಥ_ಥ", "rm 说：不允许的操作！ಥ_ಥ"),
    ("o(≧v≦)o example_app says: using recursive directories! (｡ì _ í｡)", "o(≧v≦)o example_app 说： 正在使用子路径！(｡ì _ í｡)"),
    ("o(≧v≦)o example_app says: using list options! (⊙ω⊙)", "o(≧v≦)o example_app 说： 正在使用列表选项！(⊙ω⊙)"),
]
# substitute patterns
substrules_file=r"""
{header_section}
    name test
{/header_section}
{substrules_section}
    filter_cmd rm
        [substitute_string] rm: missing operand
            locale:default rm says: missing arguments and options (>﹏<)
            locale:zh_CN rm 说：缺少参数和选项 (>﹏<)
        [/substitute_string]
        [substitute_string] type rm --help for more information
            locale:default For more information, use rm --help (｡ì _ í｡)
            locale:zh_CN 关于更多信息，请使用rm --help (｡ì _ í｡)
        [/substitute_string]

    setvar:shell (?P<shell>.+)
    [filter_cmds]
        rm -rf
        cat
        cd
        ls
    [/filter_cmds]
        [substitute_regex] {{shell}}: (?P<filename>.+): Permission denied
            locale:default \g<shell> says: Access denied to \g<filename>! ಥ_ಥ
            locale:zh_CN \g<shell> 说：文件"\g<filename>"拒绝访问！ಥ_ಥ
        # Test substvar specified in block
        [/substitute_regex] substvar

    # test substvar
    set_options substvar
    filter_cmd ls
        # testing repeated entry detection
        [substitute_regex] {{shell}}: unrecognized option '(?P<opt>.+)'
            locale:default wef
        [/substitute_regex]
        [substitute_regex] {{shell}}: unrecognized option '(?P<opt>.+)'
            locale:default \g<shell> says: option "\g<opt>" not known! (ToT)/~~~
            locale:zh_CN \g<shell> 说：未知选项"\g<opt>"！(ToT)/~~~
        [/substitute_regex]
    unset_filter_cmd

    # test substesc
    set_options substesc
    set_options strictcmdmatch
    filter_cmd example_app install-stuff
        [substitute_string] Error: sample message
            locale:default Error: {{ESC}}[1;4msample message!{{ESC}}[m (>﹏<)
            locale:zh_CN 错误：样例提示！(>﹏<)
        [/substitute_string] endmatchhere
    unset_filter_cmd

    # Test regex filter and substvar
    setvar:pattern app(_example)? (.*)install(-stuff)?
    filter_cmd_regex {{pattern}}
        [substitute_string] Error: sample message
            locale:default Error: {{ESC}}[1;4msample message!{{ESC}}[m (>﹏<)
            locale:zh_CN 错误：样例提示！(>﹏<)
        [/substitute_string] endmatchhere
    unset_filter_cmd
    set_options nosubstesc
    # global substitutions
    [substitute_regex] ^Warning:( )
        locale:default o(≧v≦)o Note:\g<1>
        locale:zh_CN o(≧v≦)o 提示：\g<1>
    [/substitute_regex]
    [substitute_regex] ^Error:( )
        locale:default (ToT)/~~~ Error:\g<1>
        locale:zh_CN (ToT)/~~~ 错误：
    [/substitute_regex]
    [substitute_regex] invalid input( )*$
        locale:default input is invalid! ಥ_ಥ
        locale:zh_CN 无效输入！ಥ_ಥ
    [/substitute_regex]

    setvar:style {{[x1b]}}[1;4m
    setvar:orig {{ESC}}[0m
    set_options exactcmdmatch
    filter_cmd rm file.ban
        [substitute_regex] (?P<shell>.+): (?P<filename>.+): Operation not permitted
            # test substchar and substesc specified in block
            [locale] default
                \g<shell> says: {{style}}Operation not permitted!{{orig}} ಥ_ಥ
            [/locale] substchar substesc
            locale:zh_CN \g<shell> 说：不允许的操作！ಥ_ಥ
        [/substitute_regex]

    set_options normalcmdmatch
    filter_cmd example_app
        [substitute_string] example_app:
            locale:default o(≧v≦)o example_app says:
            locale:zh_CN o(≧v≦)o example_app 说：
        [/substitute_string]

    # test substchar
    set_options substchar
    set_options smartcmdmatch
    filter_cmd example_app -r
        [substitute_string] using recursive directories
            # \x21=!
            locale:default using recursive directories{{[x21]}} (｡ì _ í｡)
            locale:zh_CN 正在使用子路径！(｡ì _ í｡)
        [/substitute_string]
    filter_cmd example_app -l
        [substitute_string] using list options
            locale:default using list options! (⊙ω⊙)
            locale:zh_CN 正在使用列表选项！(⊙ω⊙)
        [/substitute_string]
    set_options normalcmdmatch
{/substrules_section}
"""

db_interface.debug_mode=True
generator_path=_generator.generate_data_hierarchy(substrules_file)
db_interface.connect_db(generator_path+"/"+_globalvar.db_filename)

print("Successfully recorded data\nTesting sample outputs: ")
for x in range(len(sample_inputs)):
    inp=sample_inputs[x]
    expected=expected_outputs[x]
    content, changed_lines=db_interface.match_content(bytes(inp[0],'utf-8'),command=inp[1])
    content=content.decode('utf-8')
    if content in expected:
        print("\x1b[1;32mOK\x1b[0;1m:\x1b[0m "+content)
    else:
        print("\x1b[1;31mMismatch\x1b[0;1m:\x1b[0m "+content)

try: shutil.rmtree(generator_path)
except: pass