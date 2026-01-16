# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import shutil
import re
import difflib
from typing import Optional, Dict, List
sys.path=[f"{os.path.dirname(__file__)}/.."]+sys.path
from clitheme import _generator, _frontend_internal, _globalvar
import unittest

class TestErrors(unittest.TestCase):
    def setUp(self):
        print()
        # Ensure localization settings are correct
        _globalvar.handle_set_themedef("test")
    def _run_test(self, test_file: str, expected_msgs: Dict[str, List[str]]) -> bool:
        has_errors=False
        for lang, lines in expected_msgs.items():
            _frontend_internal.global_lang=lang
            _globalvar.msg_retrieved=False # For sanity check messages
            return_val=_generator.generate_data_hierarchy(test_file)
            generator_path=return_val.dir_path
            self.assertEqual(return_val.success, False)
            self.assertGreater(len(return_val.messages), 0)
            shutil.rmtree(generator_path)

            print('\n'.join(return_val.messages))
            if return_val.messages!=lines:
                print('\n'+'\n'.join(difflib.ndiff(lines, return_val.messages)))
                has_errors=True
        return not has_errors
    def test1_errors(self):
        filepath=re.sub(r'[\\/]', ' ', os.path.relpath(__file__))
        test_file=rf"""
        (enable_subst)
        setvar[file]: {filepath}"""+r"""
        {header}
            # linebounds-format-err
            description: |wef
        # missing-info-err
        {/header}

        # phrase-precedence-err
        !require_version 2.1

        # unknown-option-err, option-without-value-err, option-value-not-int-err, option-conflict-err
        (set_options) wef leadspaces leadtabindents:wef strictcmdmatch exactcmdmatch
        # bad-var-name-err, option-not-allowed-err
        setvar[ ESC { ]: |this| linebounds
        # phrase-format-err
        setvar[]: this

        {substrules}
            # bad-cmd-filter-pattern-err
            <filter_cmd_regex> (
            # bad-match-pattern-err
            [subst_regex] )]
                # phrase-format-err
                locale[]: this
                # (Pattern errors not shown if bad match pattern)
                default: \g
            [/subst_regex]
            [subst_regex] this
                # bad-subst-pattern-err
                default: \g
                locale[zh_CN]: \g<2>
            [/subst_regex]
        {/substrules}
        {entries}
            [entry] this
                default: that
            [/entry]
            # subsection-conflict-err
            <in_subsection> this
                [entry] that
                    default: that
                [/entry]
                [entry] another
                    default: that
                [/entry]
            <in_subsection> another
                [entry] that
                    default: that
                [/entry]
            <unset_subsection>
            # entry-conflict-err
            [entry] another
                default: that
            [/entry]
            # sanity-check-domainapp-err
            <in_domainapp> .wef ?this
            # sanity-check-subsection-err
            <in_subsection> this?
            # sanity-check-entry-err
            [entry] *this
                default: that
            [/entry]
        {/entries}
        {manpages}
            # include-file-missing-phrase-err
            <include_file> {{file}}
            # manpage-subdir-file-conflict-err
            <include_file> {{file}}
                as: man1
        {/manpages}

        # repeated-section-err
        # unterminated-section-err
        {header}
        """
        c=0
        def next(n: int): nonlocal c; c+=n; return c
        expected_msgs={}
        expected_msgs['en_US']= [
            f"Error: Line {next(6)}: Invalid line boundary format",
            f"Error: header section missing required entries: name",
            f"Error: Line {next(5)}: Header macro \"!require_version\" must be specified before other lines",
            f"Error: Line {next(3)}: Unknown option \"wef\"",
            f"Error: Line {next(0)}: No value specified for option \"leadspaces\"",
            f"Error: Line {next(0)}: The value specified for option \"leadtabindents\" is not an integer",
            f"Error: Line {next(0)}: The option \"exactcmdmatch\" can't be set at the same time with \"strictcmdmatch\"",
            f"Error: Line {next(2)}: Option \"linebounds\" not allowed here",
            f"Error: Line {next(0)}: \"ESC\" is not a valid variable name",
            f"Error: Line {next(0)}: \"{{\" is not a valid variable name",
            f"Error: Line {next(2)}: Invalid format for \"setvar\"",
            f"Error: Line {next(4)}: Bad command filter pattern (missing ), unterminated subpattern at position 0)",
            f"Error: Line {next(2)}: Bad match pattern (unbalanced parenthesis at position 0)",
            f"Error: Line {next(2)}: Invalid format for \"locale\"",
            f"Error: Line {next(6)}: Bad substitute pattern (missing < at position 2)",
            f"Error: Line {next(1)}: Bad substitute pattern (invalid group reference 2 at position 3)",
            f"Error: Line {next(9)}>{c+1}[default]: Cannot create subsection \"this\" because an entry with the same name already exists",
            f"Error: Line {next(3)}>{c+1}[default]: Cannot create subsection \"this\" because an entry with the same name already exists",
            f"Error: Line {next(9)}>{c+1}[default]: Cannot create entry \"another\" because a subsection with the same name already exists",
            f"Error: Line {next(4)}: Domain and app names cannot start with '.'",
            f"Error: Line {next(2)}: Subsection names cannot contain '?'",
            f"Error: Line {next(2)}: Entry subsections/names cannot contain '*'",
            f"Error: Line {next(7)}: Missing \"as <filename>\" phrase on next line",
            f"Error: Line {next(7)}: Repeated header section",
            f"Error: Unterminated header section at end of file",
            f"Error: Missing or incomplete header or content sections",
        ]
        c=0
        expected_msgs['zh_CN']=[
            f"错误：第{next(6)}行：无效的行边界格式",
            f"错误：header段落缺少必要条目：name",
            f"错误：第{next(5)}行：头定义\"!require_version\"必须在其他行之前声明",
            f"错误：第{next(3)}行：未知选项\"wef\"",
            f"错误：第{next(0)}行：选项\"leadspaces\"未指定数值",
            f"错误：第{next(0)}行：选项\"leadtabindents\"指定的数值不是整数",
            f"错误：第{next(0)}行：选项\"exactcmdmatch\"和\"strictcmdmatch\"不能同时指定",
            f"错误：第{next(2)}行：选项\"linebounds\"不允许在这里指定",
            f"错误：第{next(0)}行：\"ESC\"不是一个有效的变量名称",
            f"错误：第{next(0)}行：\"{{\"不是一个有效的变量名称",
            f"错误：第{next(2)}行：无效的\"setvar\"格式",
            f"错误：第{next(4)}行：无效的命令限制正则表达式（missing ), unterminated subpattern at position 0）",
            f"错误：第{next(2)}行：无效的匹配正则表达式（unbalanced parenthesis at position 0）",
            f"错误：第{next(2)}行：无效的\"locale\"格式",
            f"错误：第{next(6)}行：无效的替换正则表达式（missing < at position 2）",
            f"错误：第{next(1)}行：无效的替换正则表达式（invalid group reference 2 at position 3）",
            f"错误：第{next(9)}>{c+1}[default]行：无法创建子路径\"this\"，因为拥有相同名称的定义已存在",
            f"错误：第{next(3)}>{c+1}[default]行：无法创建子路径\"this\"，因为拥有相同名称的定义已存在",
            f"错误：第{next(9)}>{c+1}[default]行：无法创建定义\"another\"，因为拥有相同名称的子路径已存在",
            f"错误：第{next(4)}行：开发者和应用程序名称不能以'.'开头",
            f"错误：第{next(2)}行：子路径名称不能包含'?'",
            f"错误：第{next(2)}行：定义路径名称不能包含'*'",
            f"错误：第{next(7)}行：在下一行缺少\"as <文件名>\"语句",
            f"错误：第{next(7)}行：重复的header段落",
            f"错误：在文件结尾未结束header段落",
            f"错误：文件缺少或包含不完整的header或内容段落",
        ]
        self.assertTrue(self._run_test(test_file, expected_msgs), "Messages do not match")
    def test2_syntax_errors(self):
        sc=True
        # invalid-phrase-err
        sc=sc and self._run_test(
            test_file="wef",
            expected_msgs={
                'en_US': ["Syntax error: Line 1: Unexpected \"wef\""],
                'zh_CN': ["语法错误：第1行：无效的\"wef\"语句"]
            }
        )
        # invalid-version-err
        sc=sc and self._run_test(
            test_file="!require_version wef",
            expected_msgs={
                'en_US': ["Syntax error: Line 1: Invalid version information \"wef\""],
                'zh_CN': ["语法错误：第1行：无效版本信息\"wef\""]
            }
        )
        # unsupported-version-err
        sc=sc and self._run_test(
            test_file="!require_version 123.0",
            expected_msgs={
                'en_US': [f"Current version of CLItheme ({_globalvar.clitheme_version}) does not support this file (requires 123.0 or higher)"],
                'zh_CN': [f"当前版本的CLItheme（{_globalvar.clitheme_version}）不支持此文件（需要 123.0 或更高版本）"]
            }
        )
        # unterminated-content-block-err
        sc=sc and self._run_test(
            test_file="{header}\n[description]",
            expected_msgs={
                'en_US': ["Syntax error: Line 2: Unterminated content block"],
                'zh_CN': ["语法错误：第2行：未结束的文本段落"]
            }
        )
        # extra-arguments-err
        sc=sc and self._run_test(
            test_file="{header} wef wef",
            expected_msgs={
                'en_US': ["Syntax error: Line 1: Extra arguments after \"{header}\""],
                'zh_CN': ["语法错误：第1行：\"{header}\"后的参数太多"]
            }
        )
        # not-enough-args-err
        sc=sc and self._run_test(
            test_file="{entries}\n[entry]",
            expected_msgs={
                'en_US': ["Syntax error: Line 2: Not enough arguments for \"[entry]\""],
                'zh_CN': ["语法错误：第2行：\"[entry]\"后参数不够"]
            }
        )
        self.assertTrue(sc, "Message mismatch detected")
    def test3_warnings(self):
        test_file=r"""
        {substrules}
            # Test "Option not enabled" warnings
            setvar[_var]: {{[invalid]}} {{ESC}} 
            [subst_string] |{{ESC}} {{[x1b]}} {{_var}}|
                default: None
            [/subst_string]
            (set_options) substvar linebounds
            [subst_string] |{{_var}}|
                default: None
            [/subst_string]
            # Test subst warnings
            (enable_subst)
            [subst_string] |{{_var}} {{[xgg]}} {{nonexistent}}|
                default: None
            [/subst_string]

            # testing repeated entry detection
            setvar[shell shell2]: (?P<shell>.+)
            [subst_regex] {{shell}}: unrecognized option '(?P<opt>.+)'
                locale[default zh_CN zh]: (Error: Repeated entry detection failed)
            [/subst_regex]
            # {{shell}} should equal to {{shell2}} 
            [subst_regex] {{shell2}}: unrecognized option '(?P<opt>.+)'
                default: \g<shell> says: option "\g<opt>" not known! (ToT)/~~~
                locale[zh_CN zh]: \g<shell> 说：未知选项"\g<opt>"！(ToT)/~~~
            [/subst_regex]
        {/substrules}
        # Test repeated entries detection
        {entries}
            [entry] this and that
                default: that
            [/entry]
            <in_domainapp> this and
            [entry] that
                default: that
            [/entry]
            <unset_domainapp>
            <in_subsection> this and
            [entry] that
            [entry] that
                default: that
            [/entry]
        {/entries}
        {header}
            name: This
            name: That
        {/header}
        {manpages}
            [file_content] man1 this.1
            [file_content] man1 this.1
                {{wef}}
            [/file_content] substvar
        {/manpages}
        end
        """
        c=0
        def next(n: int): nonlocal c; c+=n; return c
        expected_msgs={}
        expected_msgs['en_US']=[
            f"Warning: Line {next(5)}: Attempted to use line boundaries, but \"linebounds\" option is not enabled",
            f"Warning: Line {next(0)}: Attempted to reference a defined variable, but \"substvar\" option is not enabled",
            f"Warning: Line {next(0)}: Attempted to use \"{{{{ESC}}}}\", but \"substesc\" option is not enabled",
            f"Warning: Line {next(0)}: Attempted to use character substitution, but \"substchar\" option is not enabled",
            f"Warning: Line {next(4)}: Attempted to use \"{{{{ESC}}}}\", but \"substesc\" option is not enabled",
            f"Warning: Line {next(0)}: Attempted to use character substitution, but \"substchar\" option is not enabled",
            f"Warning: Line {next(5)}: Unknown variable \"nonexistent\", not performing substitution",
            f"Warning: Line {next(0)}: Invalid substchar format \"invalid\", not performing substitution",
            f"Warning: Line {next(0)}: Invalid character code \"gg\", not performing substitution",
            f"Warning: Line {next(10)}>{c+1}[default]: Repeated substrules entry, overwriting",
            f"Warning: Line {next(0)}>{c+2}[zh_CN]: Repeated substrules entry, overwriting",
            f"Warning: Line {next(0)}>{c+2}[zh]: Repeated substrules entry, overwriting",
            f"Warning: Line {next(11)}>{c+1}[default]: Repeated entry \"this and that\", overwriting",
            f"Warning: Line {next(5)}>{c+2}[default]: Repeated entry \"this and that\", overwriting",
            f"Warning: Line {next(1)}>{c+1}[default]: Repeated entry \"this and that\", overwriting",
            f"Warning: Line {next(6)}: Repeated header info \"name\", overwriting",
            f"Warning: Line {next(5)}: Unknown variable \"wef\", not performing substitution",
            f"Warning: Line {next(-1)}: Repeated manpage file, overwriting",
            f"Syntax error: Line {next(4)}: Unexpected \"end\"",
        ]
        c=0
        expected_msgs['zh_CN']=[
            f"警告：第{next(5)}行：尝试使用行边界，但\"linebounds\"选项未被启用",
            f"警告：第{next(0)}行：尝试引用定义的变量，但\"substvar\"选项未被启用",
            f"警告：第{next(0)}行：尝试引用\"{{{{ESC}}}}\"，但\"substesc\"选项未被启用",
            f"警告：第{next(0)}行：尝试使用字符替换，但\"substchar\"选项未被启用",
            f"警告：第{next(4)}行：尝试引用\"{{{{ESC}}}}\"，但\"substesc\"选项未被启用",
            f"警告：第{next(0)}行：尝试使用字符替换，但\"substchar\"选项未被启用",
            f"警告：第{next(5)}行：未知变量名称\"nonexistent\"，不会进行替换",
            f"警告：第{next(0)}行：无效的substchar格式\"invalid\"，不会进行替换",
            f"警告：第{next(0)}行：无效字符代码\"gg\"，不会进行替换",
            f"警告：第{next(10)}>{c+1}[default]行：重复的substrules定义；之前的定义内容将会被覆盖",
            f"警告：第{next(0)}>{c+2}[zh_CN]行：重复的substrules定义；之前的定义内容将会被覆盖",
            f"警告：第{next(0)}>{c+2}[zh]行：重复的substrules定义；之前的定义内容将会被覆盖",
            f"警告：第{next(11)}>{c+1}[default]行：重复的定义\"this and that\"；之前的定义内容将会被覆盖",
            f"警告：第{next(5)}>{c+2}[default]行：重复的定义\"this and that\"；之前的定义内容将会被覆盖",
            f"警告：第{next(1)}>{c+1}[default]行：重复的定义\"this and that\"；之前的定义内容将会被覆盖",
            f"警告：第{next(6)}行：重复的header信息\"name\"；之前的定义内容将会被覆盖",
            f"警告：第{next(5)}行：未知变量名称\"wef\"，不会进行替换",
            f"警告：第{next(-1)}行：重复的manpage文件；之前的文件内容将会被覆盖",
            f"语法错误：第{next(4)}行：无效的\"end\"语句",
        ]
        self.assertTrue(self._run_test(test_file, expected_msgs), "Messages do not match")

if __name__ == "__main__":
    unittest.main()