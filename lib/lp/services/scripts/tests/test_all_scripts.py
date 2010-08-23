# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Check the integrity of the /scripts and /cronscripts."""

__metaclass__ = type
__all__ = []

import os
import unittest

from lp.services.scripts.tests import find_lp_scripts
from lp.testing import (
    run_script,
    TestCase,
    )


class ScriptsTestCase(TestCase):
    """Check the integrity of all scripts shipped in the tree."""

    def test_scripts(self):
        # Walk through all scripts and check if they can run successfully
        # if passed '-h' (optparser help). We run the scripts in a clean
        # shell environment, i.e not PYTHONPATH set.
        bad = []
        for script_path in find_lp_scripts():
            cmd_line = script_path + " -h"
            out, err, returncode = run_script(cmd_line)
            if returncode != os.EX_OK:
                bad.append("%s failed\n%s" % (script_path, err))
        self.failIf(bad, '\n\n'.join(bad))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
