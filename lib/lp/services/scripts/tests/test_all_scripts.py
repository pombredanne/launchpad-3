# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Check the integrity of the /scripts and /cronscripts."""

__metaclass__ = type

import doctest
import os

from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from testtools.matchers import DocTestMatches

from lp.services.scripts.tests import find_lp_scripts
from lp.testing import (
    run_script,
    TestCase,
    )


def make_id(script_path):
    return 'script_' + os.path.splitext(os.path.basename(script_path))[0]


class ScriptsTestCase(WithScenarios, TestCase):
    """Check the integrity of all scripts shipped in the tree."""

    scenarios = [
        (make_id(script_path), {'script_path': script_path})
        for script_path in find_lp_scripts()]

    def test_script(self):
        # Run self.script_path with '-h' to make sure it runs cleanly.
        cmd_line = self.script_path + " -h"
        out, err, returncode = run_script(cmd_line)
        self.assertThat(err, DocTestMatches('', doctest.REPORT_NDIFF))
        self.assertEqual('', err)
        self.assertEqual(os.EX_OK, returncode)


load_tests = load_tests_apply_scenarios
