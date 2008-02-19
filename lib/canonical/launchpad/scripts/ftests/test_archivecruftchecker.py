# Copyright 2007 Canonical Ltd.  All rights reserved.
"""ArchiveCruftChecker tests.

Check how scripts/ftpmaster-tools/archive-cruft-check.py works on a
just-published 'ubuntutest' archive.
"""

__metaclass__ = type

from unittest import TestLoader
import shutil
import subprocess
import os
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import (
    IDistributionSet, PackagePublishingPocket)
from canonical.launchpad.scripts.ftests.test_ftpmaster import LocalLogger
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveCruftChecker, ArchiveCruftCheckerError)

# XXX cprov 2006-05-15: {create, remove}TestArchive functions should be
# moved to the publisher test domain as soon as we have it.
def createTestArchive():
    """Creates a fresh test archive based on sampledata."""
    script = os.path.join(config.root, "scripts", "publish-distro.py")
    process = subprocess.Popen([sys.executable, script, "-C", "-q",
                                "-d", 'ubuntutest'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    garbage = process.stderr.read()
    garbage = process.stdout.read()
    return process.wait()


def removeTestArchive():
    """Remove the entire test archive directory from the filesystem."""
    shutil.rmtree("/var/tmp/archive/")


class TestArchiveCruftChecker(LaunchpadZopelessTestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Setup the test environment.

        Retrieve useful instances and create a test archive.
        """
        LaunchpadZopelessTestCase.setUp(self)
        self.log = LocalLogger()

        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.breezy_autotest = self.ubuntutest['breezy-autotest']
        self.archive_path = "/var/tmp/archive"
        createTestArchive()

    def tearDown(self):
        """Clean up test environment and remove the test archive."""
        LaunchpadZopelessTestCase.tearDown(self)
        removeTestArchive()

    def test_initialize_success(self):
        """Test ArchiveCruftChecker initialization process.

        Check if the correct attributes are built after initialization.
        """
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntutest', suite='breezy-autotest',
            archive_path=self.archive_path)
        checker.initialize()
        self.assertEqual(self.ubuntutest, checker.distro)
        self.assertEqual(self.breezy_autotest, checker.distroseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, checker.pocket)
        self.assertEqual(0, len(checker.nbs_to_remove))
        self.assertEqual(0, len(checker.real_nbs))
        self.assertEqual(0, len(checker.dubious_nbs))
        self.assertEqual(0, len(checker.bin_pkgs))
        self.assertEqual(0, len(checker.arch_any))
        self.assertEqual(0, len(checker.source_versions))
        self.assertEqual(0, len(checker.source_binaries))
        self.log.read()

    def test_initialize_unknown_suite(self):
        """ArchiveCruftChecker should raise on an unknown suite."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='misarable',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()

    def test_initialize_unknown_distribution(self):
        """ArchiveCruftChecker should raise on an unknown distribution."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='foobuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()

    def test_initialize_no_distro_in_archive(self):
        """ArchiveCruftChecker should raise on the absence of distribution."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
