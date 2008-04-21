# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Build log sanitization (removal of passwords from buildlog URLs) tests."""

__metaclass__ = type

import difflib
import os
import shutil
import unittest

from ConfigParser import SafeConfigParser

from canonical.buildd.slave import BuildDSlave

class MockBuildManager(object):
    """Mock BuildManager class."""
    is_archive_private = False

class BuildlogSecurityTests(unittest.TestCase):
    """Unit tests for scrubbing (removal of passwords) of buildlog files."""

    def setUp(self):
        self.cwd = os.path.join(os.path.dirname(__file__))
        conffile = os.path.join(self.cwd, 'buildd-slave-test.conf')
        conf = SafeConfigParser()
        conf.read(conffile)
        self.cache_path = conf.get("slave","filecache")
        if os.path.isdir(self.cache_path):
            shutil.rmtree(self.cache_path)
        os.makedirs(self.cache_path)
        self.slave = BuildDSlave(conf)

    def testBuildlogScrubbing(self):
        """Tests the buildlog scrubbing (removal of passwords from URLs)."""
        # Copy the fake buildlog file to the cache path.
        shutil.copy('%s%sbuildlog' % (self.cwd, os.sep), self.cache_path)

        # This is where the slave leaves the original/unsanitized
        # buildlog file after scrubbing.
        unsanitized_path = '%s%sbuildlog.unsanitized' % (
            (self.cache_path, os.sep))
        # The scrubbed buildlog content will be here.
        clean_path = '%s%sbuildlog' % (self.cache_path, os.sep)

        # Invoke the slave's buildlog scrubbing method.
        self.slave.sanitizeBuildlog(
            '%s%sbuildlog' % (self.cache_path, os.sep))

        # Read the unsanitized original content.
        unsanitized = open(unsanitized_path).read().splitlines()
        # Read the new sanitized content.
        clean = open(clean_path).read().splitlines()

        # Compare the scrubbed content with the unsanitized one.
        differences = '\n'.join(difflib.context_diff(unsanitized, clean))

        # Read the expected differences from the prepared disk file.
        expected = open('%s%stest_1.diff' % (self.cwd, os.sep)).read()

        # Make sure they match.
        self.assertEqual(differences, expected)

    def testLogtailScrubbing(self):
        """Test the scrubbing of the slave's getLogTail() output."""

        # This is where the buildlog file lives.
        log_path = '%s%sbuildlog' % (self.cache_path, os.sep)

        # Copy the prepared, longer buildlog file so we can test lines
        # that are chopped off in the middle.
        shutil.copy('%s%sbuildlog.long' % (self.cwd, os.sep), log_path)

        # Make slave believe that logging is turned on.
        self.slave._log = True

        # First get the unfiltered log tail output.
        self.slave.manager = MockBuildManager()
        unsanitized = self.slave.getLogTail().splitlines()

        # Make the slave believe we are building in a private archive to
        # obtain the scrubbed log tail output.
        self.slave.manager.is_archive_private = True
        clean = self.slave.getLogTail().splitlines()

        # Get the differences ..
        differences = '\n'.join(difflib.context_diff(unsanitized, clean))

        # .. and the expected differences.
        expected = open('%s%stest_2.diff' % (self.cwd, os.sep)).read()

        # Finally make sure what we got is what we expected.
        self.assertEqual(differences, expected)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
