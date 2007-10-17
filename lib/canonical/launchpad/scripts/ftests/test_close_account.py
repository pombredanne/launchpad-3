# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the close-account.py script as best we can.

Unfortunately, we have no way of detecting schema updates containing new
information that needs to be removed or sanitized on account closure apart
from reviewers noticing and prompting developers to update this script.

See Bug #120506
"""

__metaclass__ = type
__all__ = []

import os.path
import re
import subprocess
import unittest

from canonical.config import config
from canonical.testing import DatabaseLayer

class CloseAccountScriptTestCase(unittest.TestCase):
    layer = DatabaseLayer

    def tearDown(self):
        DatabaseLayer.force_dirty_database()

    def testCloseAccount(self):
        script = os.path.join(config.root, 'scripts', 'close-account.py')
        proc = subprocess.Popen(
                [script, 'mark@hbd.com'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        out, err = proc.communicate()
        out_lines = out.splitlines()
        self.failUnlessEqual(
                len(out_lines), 1, 'Too much output\n%s' % out_lines)

        expected = "^.*INFO\s+Closing sabdfl's account$"
        self.failUnless(
                re.search(expected, out_lines[0]) is not None,
                'Invalid line %s' % out_lines[0])

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CloseAccountScriptTestCase))
    return suite

