# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Buildd tests."""

__metaclass__ = type
__all__ = ['BuildlogSecurityTests']

import difflib
import os
import shutil
import tempfile
import urllib2
import unittest

from ConfigParser import SafeConfigParser

from canonical.buildd.slave import BuildDSlave


def read_file(path):
    """Helper for reading the contents of a file."""
    file_object = open(path)
    try:
        return file_object.read()
    finally:
        file_object.close()


class MockBuildManager(object):
    """Mock BuildManager class."""
    is_archive_private = False


class BuildlogSecurityTests(unittest.TestCase):
    """Unit tests for the buildd slave."""

    def setUp(self):
        self.here = os.path.abspath(os.path.dirname(__file__))
        conffile = os.path.join(self.here, 'buildd-slave-test.conf')
        conf = SafeConfigParser()
        conf.read(conffile)
        self.cache_path = tempfile.mkdtemp()
        conf.set("slave", "filecache", self.cache_path)
        self.slave = BuildDSlave(conf)

    def tearDown(self):
        if os.path.isdir(self.cache_path):
            shutil.rmtree(self.cache_path)

    def testBasicAuth(self):
        """Test that the auth handler is installed with the right details."""
        url = "http://fakeurl/"
        user = "myuser"
        password = "fakepassword"

        self.slave.installAuthHandler(url, user, password)

        # Inspect urllib2's opener.
        password_mgr = urllib2._opener.handlers[-2].passwd
        stored_user, stored_pass = password_mgr.find_user_password(None, url)
        self.assertEqual(user, stored_user)
        self.assertEqual(password, stored_pass)

    def testBuildlogScrubbing(self):
        """Tests the buildlog scrubbing (removal of passwords from URLs)."""
        # This is where the buildlog file lives.
        log_path = os.path.join(self.cache_path, 'buildlog')

        # This is where the slave leaves the original/unsanitized
        # buildlog file after scrubbing.
        unsanitized_path = os.path.join(self.cache_path,
                                        'buildlog.unsanitized')

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
        log_path = os.path.join(self.cache_path, 'buildlog')

        # Copy the prepared, longer buildlog file so we can test lines
        # that are chopped off in the middle.
        shutil.copy(os.path.join(self.here, 'buildlog.long'), log_path)

        # Make slave believe that logging is turned on.
        self.slave._log = tempfile.TemporaryFile()

        # First get the unfiltered log tail output (which is the default
        # behaviour because the BuildManager's 'is_archive_private'
        # property is initialized to False).
        self.slave.manager = MockBuildManager()
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
