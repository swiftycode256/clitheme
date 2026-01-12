# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import shutil
import re
from typing import Optional
sys.path=[f"{os.path.dirname(__file__)}/.."]+sys.path
from clitheme import _generator, _globalvar
import unittest
import warnings

class TestErrors(unittest.TestCase):

    def setUp(self):
        print()
        warnings.simplefilter("ignore")
        self.generator_path: Optional[str]=None
    def tearDown(self):
        if self.generator_path!=None:
            shutil.rmtree(self.generator_path)
    def test_errors(self):
        filepath=re.sub(r'[\\/]', ' ', os.path.relpath(__file__))
        test_file=rf"""
        (enable_subst)
        setvar[file]: {filepath}
        """+\
        r"""
        # missing-info-err
        {header}
            # linebounds-format-err
            description: |wef
        {/header}

        # phrase-precedence-err
        !require_version 2.1

        # [Option errors]
        (set_options) wef leadspaces leadtabindents:wef strictcmdmatch exactcmdmatch
        # bad-var-name-err and Option errors
        setvar[ESC { }]: |this| linebounds
        # phrase-format-err
        setvar[]: this

        {substrules}
            # bad-cmd-filter-pattern-err
            <filter_cmd> (
            # bad-match-pattern-err
            [subst_regex] )]
                # bad-subst-pattern-err
                default: \g
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
        {/entries}
        {manpages}
            # include-file-missing-phrase-err
            <include_file> {{file}}
            # include-file-read-err
            <include_file> nonexistent
                as: man1 test.1
            # manpage-subdir-file-conflict-err
            <include_file> {{file}}
                as: man1
        {/manpages}

        # repeated-section-err
        # unterminated-section-err
        {header}
        """
        return_val=_generator.generate_data_hierarchy(test_file)
        self.generator_path=return_val.dir_path
        self.assertEqual(return_val.success, False)
        self.assertGreater(len(return_val.messages), 0)
        print("\n".join(return_val.messages))

# Syntax errors:
# invalid-version-err
# unterminated-content-block-err
# unsupported-version-err
# extra-arguments-err
# not-enough-args-err
# invalid-phrase-err

if __name__ == "__main__":
    unittest.main()