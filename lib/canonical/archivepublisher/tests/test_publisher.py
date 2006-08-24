# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for publishing.py"""

__metaclass__ = type

import shutil
import unittest

from zope.component import getUtility

from canonical.archivepublisher.config import Config
from canonical.archivepublisher.pool import (
    DiskPool, Poolifier)
from canonical.archivepublisher.tests.util import FakeLogger
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import IDistributionSet
from canonical.librarian.client import LibrarianClient


class TestPublisher(LaunchpadZopelessTestCase):
    dbuser = 'lucille'

    # Setup creates a pool dir...
    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.library = LibrarianClient()
        self._distribution = getUtility(IDistributionSet)['ubuntutest']
        self._config = Config(self._distribution)
        self._config.setupArchiveDirs()

        self._pooldir = self._config.poolroot
        self._overdir = self._config.overrideroot
        self._listdir = self._config.overrideroot
        self._logger = FakeLogger()
        self._dp = DiskPool(Poolifier(), self._pooldir, self._logger)

    # Tear down blows the pool dir away...
    def tearDown(self):
        LaunchpadZopelessTestCase.tearDown(self)
        shutil.rmtree(self._config.distroroot)

    def testInstantiate(self):
        """canonical.archivepublisher.Publisher should be instantiatable"""
        from canonical.archivepublisher import Publisher
        Publisher(self._logger, self._config, self._dp, self._distribution)

    def testPathFor(self):
        """canonical.archivepublisher.Publisher._pathfor should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, self._config, self._dp, self._distribution)
        cases = (
            ("main", "foo", None, "%s/main/f/foo" % self._config.poolroot),
            ("main", "foo", "foo.deb", "%s/main/f/foo/foo.deb"
             % self._config.poolroot)
            )
        for case in cases:
            self.assertEqual(case[3],
                p._diskpool.pathFor(case[0], case[1], case[2]) )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

