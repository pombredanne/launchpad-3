# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the initialise_distroseries script machinery."""

__metaclass__ = type

import os
import subprocess
import sys
from zope.component import getUtility

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.scripts.initialise_distroseries import (
    InitialiseDistroSeries, InitialisationError)
from lp.testing import TestCaseWithFactory

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.ftests import login, logout
from canonical.testing.layers import LaunchpadZopelessLayer


class TestInitialiseDistroSeries(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitialiseDistroSeries, self).setUp()
        login("foo.bar@canonical.com")
        distribution_set = getUtility(IDistributionSet)
        self.ubuntutest = distribution_set['ubuntutest']
        self.ubuntu = distribution_set['ubuntu']
        self.hoary = self.ubuntu['hoary']
        logout()

    def _create_distroseries(self, parent_series):
        login("foo.bar@canonical.com")
        foobuntu = self.ubuntutest.newSeries(
            'foobuntu', 'FooBuntu', 'The Foobuntu', 'yeck', 'doom',
            '888', parent_series, self.hoary.owner)
        logout()
        return foobuntu

    def test_failure_with_no_parent_series(self):
        foobuntu = self._create_distroseries(None)
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaises(InitialisationError, ids.check)

    def test_failure_for_already_released_distroseries(self):
        login("foo.bar@canonical.com")
        ids = InitialiseDistroSeries(self.ubuntutest['breezy-autotest'])
        self.assertRaises(InitialisationError, ids.check)
        logout()

    def test_failure_with_pending_builds(self):
        foobuntu = self._create_distroseries(self.hoary)
        login("foo.bar@canonical.com")
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaises(InitialisationError, ids.check)
        logout()

    def test_failure_with_queue_items(self):
        foobuntu = self._create_distroseries(
            self.ubuntutest['breezy-autotest'])
        login('foo.bar@canonical.com')
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaises(InitialisationError, ids.check)
        logout()

    def test_initialise(self):
        foobuntu = self._create_distroseries(self.hoary)
        login("foo.bar@canonical.com")
        pending_builds = self.hoary.getBuildRecords(
            BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)
        for build in pending_builds:
            build.status = BuildStatus.FAILEDTOBUILD
        ids = InitialiseDistroSeries(foobuntu)
        ids.check()
        ids.initialise()
        hoary_pmount_pubs = self.hoary.getPublishedReleases('pmount')
        foobuntu_pmount_pubs = foobuntu.getPublishedReleases('pmount')
        self.assertEqual(len(hoary_pmount_pubs), len(foobuntu_pmount_pubs))

    def test_script(self):
        foobuntu = self._create_distroseries(self.hoary)
        ifp = os.path.join(
            config.root, 'scripts', 'ftpmaster-tools',
            'initialise-from-parent.py')
        process = subprocess.Popen(
            [sys.executable, ifp, "-vv", "-d", "ubuntutest", "foobuntu"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        print stderr
        self.assertEqual(process.returncode, 0)
        login("foo.bar@canonical.com")
        hoary_pmount_pubs = self.hoary.getPublishedReleases('pmount')
        foobuntu_pmount_pubs = foobuntu.getPublishedReleases('pmount')
        self.assertEqual(len(hoary_pmount_pubs), len(foobuntu_pmount_pubs))

