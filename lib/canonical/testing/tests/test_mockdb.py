# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the mockdb module."""

__metaclass__ = type
__all__ = []

from doctest import DocTestSuite
import os
import os.path
import unittest

from canonical.testing import mockdb


class MockDbTestCase(unittest.TestCase):

    def setUp(self):
        self.script_filename = mockdb.script_filename('_mockdb_unittest')

    def tearDown(self):
        if os.path.exists(self.script_filename):
            os.unlink(self.script_filename)

    def testSerialize(self):
        # Ensure the scripts can store and retrieve their logs
        recorder = mockdb.ScriptRecorder(self.script_filename)
        recorder.log = ['Arbitrary Data']
        recorder.store()

        replayer = mockdb.ScriptPlayer(self.script_filename)
        self.failUnlessEqual(replayer.log, ['Arbitrary Data'])

    def testScriptFilename(self):
        # Ensure evil characters in the key don't mess up the script_filename
        # results. Only '/' is really evil - other chars should all work
        # fine but we might as well sanitise ones that might be annoying.
        evil_chars = ['/', ' ', '*', '?', '~', '\0']
        for key in evil_chars:
            for pattern in ['%s', 'x%s', '%sy', 'x%sy']:
                path = mockdb.script_filename(pattern % key)

                # Ensure our initial path is correct
                self.failUnlessEqual(
                        os.path.commonprefix([mockdb.SCRIPT_DIR, path]),
                        mockdb.SCRIPT_DIR)

                # And there are no path segments
                self.failUnlessEqual(os.path.dirname(path), mockdb.SCRIPT_DIR)

                # And that the filename contains no evil or annoying
                # characters.
                filename = os.path.basename(path)
                self.failIfEqual(filename, '')
                for evil_char in evil_chars:
                    self.failIf(evil_char in filename)

    _retry_count = 0


_doctest_retry_count = 0


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    suite.addTest(DocTestSuite())
    return suite

