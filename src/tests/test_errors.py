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
from clitheme import _generator, frontend, _globalvar
import unittest
import warnings

class TestErrors(unittest.TestCase):
    def setUp(self):
        print()
        warnings.simplefilter("ignore")
        # Ensure localization settings are correct
        _globalvar.handle_set_themedef("test")
    def _run_test(self, test_file: str, expected_msgs: Dict[str, List[str]]):
        for lang, lines in expected_msgs.items():
            frontend.global_lang=lang
            _globalvar.msg_retrieved=False # For sanity check messages
            return_val=_generator.generate_data_hierarchy(test_file)
            generator_path=return_val.dir_path
            self.assertEqual(return_val.success, False)
            self.assertGreater(len(return_val.messages), 0)
            shutil.rmtree(generator_path)

            print('\n'.join(return_val.messages))
            if return_val.messages!=lines:
                print('\n'+'\n'.join(difflib.ndiff(lines, return_val.messages)))
                self.fail("Messages not equal")
    def test_errors(self):
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
            f"Error: Line {next(10)}: Cannot create subsection \"this\" because an entry with the same name already exists",
            f"Error: Line {next(3)}: Cannot create subsection \"this\" because an entry with the same name already exists",
            f"Error: Line {next(9)}: Cannot create entry \"another\" because a subsection with the same name already exists",
            f"Error: Line {next(3)}: Domain and app names cannot start with '.'",
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
            f"错误：第{next(10)}行：无法创建子路径\"this\"，因为拥有相同名称的定义已存在",
            f"错误：第{next(3)}行：无法创建子路径\"this\"，因为拥有相同名称的定义已存在",
            f"错误：第{next(9)}行：无法创建定义\"another\"，因为拥有相同名称的子路径已存在",
            f"错误：第{next(3)}行：开发者和应用程序名称不能以'.'开头",
            f"错误：第{next(2)}行：子路径名称不能包含'?'",
            f"错误：第{next(2)}行：定义路径名称不能包含'*'",
            f"错误：第{next(7)}行：在下一行缺少\"as <文件名>\"语句",
            f"错误：第{next(7)}行：重复的header段落",
            f"错误：在文件结尾未结束header段落",
            f"错误：文件缺少或包含不完整的header或内容段落",
        ]
        self._run_test(test_file, expected_msgs)

# Syntax errors:
# invalid-version-err
# unterminated-content-block-err
# unsupported-version-err
# extra-arguments-err
# not-enough-args-err
# invalid-phrase-err

if __name__ == "__main__":
    unittest.main()