# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""Buildd tests.

Build log sanitization (removal of passwords from buildlog URLs) tests.
"""

__metaclass__ = type

__all__ = ['BuildlogSecurityTests']

import difflib
import os
import shutil
import tempfile
import urllib2
import unittest

from canonical.buildd.ftests.harness import BuilddTestCase


def read_file(path):
    """Helper for reading the contents of a file."""
    file_object = open(path)
    try:
        return file_object.read()
    finally:
        file_object.close()


class BuildlogSecurityTests(BuilddTestCase):
    """Unit tests for scrubbing (removal of passwords) of buildlog files."""

    def testBasicAuth(self):
        """Test that the auth handler is installed with the right details."""
        url = "http://fakeurl/"
        user = "myuser"
        password = "fakepassword"

        opener = self.slave.setupAuthHandler(url, user, password)

        # Inspect the opener.
        for handler in opener.handlers:
            if isinstance(handler, urllib2.HTTPBasicAuthHandler):
                break
        password_mgr = handler.passwd
        stored_user, stored_pass = password_mgr.find_user_password(None, url)
        self.assertEqual(user, stored_user)
        self.assertEqual(password, stored_pass)

    def testBuildlogScrubbing(self):
        """Tests the buildlog scrubbing (removal of passwords from URLs)."""
        # This is where the buildlog file lives.
        log_path = self.slave.cachePath('buildlog')

        # This is where the slave leaves the original/unsanitized
        # buildlog file after scrubbing.
        unsanitized_path = self.slave.cachePath('buildlog.unsanitized')

        # Copy the fake buildlog file to the cache path.
        shutil.copy(os.path.join(self.here, 'buildlog'), log_path)

        # Invoke the slave's buildlog scrubbing method.
        self.slave.sanitizeBuildlog(log_path)

        # Read the unsanitized original content.
        unsanitized = read_file(unsanitized_path).splitlines()
        # Read the new, sanitized content.
        clean = read_file(log_path).splitlines()

        # Compare the scrubbed content with the unsanitized one.
        differences = '\n'.join(difflib.unified_diff(unsanitized, clean))

        # Read the expected differences from the prepared disk file.
        expected = read_file(os.path.join(self.here, 'test_1.diff'))

        # Make sure they match.
        self.assertEqual(differences, expected)

    def testLogtailScrubbing(self):
        """Test the scrubbing of the slave's getLogTail() output."""

        # This is where the buildlog file lives.
        log_path = self.slave.cachePath('buildlog')

        # Copy the prepared, longer buildlog file so we can test lines
        # that are chopped off in the middle.
        shutil.copy(os.path.join(self.here, 'buildlog.long'), log_path)

        # First get the unfiltered log tail output (which is the default
        # behaviour because the BuildManager's 'is_archive_private'
        # property is initialized to False).
        self.slave.manager.is_archive_private = False
        unsanitized = self.slave.getLogTail().splitlines()

        # Make the slave believe we are building in a private archive to
        # obtain the scrubbed log tail output.
        self.slave.manager.is_archive_private = True
        clean = self.slave.getLogTail().splitlines()

        # Get the differences ..
        differences = '\n'.join(difflib.unified_diff(unsanitized, clean))

        # .. and the expected differences.
        expected = read_file(os.path.join(self.here, 'test_2.diff'))

        # Finally make sure what we got is what we expected.
        self.assertEqual(differences, expected)

    def testLogtail(self):
        """Tests the logtail mechanisms.

        'getLogTail' return up to 2 KiB text from the current 'buildlog' file.
        """
        self.makeLog(0)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 0)

        self.makeLog(1)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 1)

        self.makeLog(2048)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)

        self.makeLog(2049)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)

        self.makeLog(4096)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
