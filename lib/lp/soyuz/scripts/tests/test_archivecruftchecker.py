# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveCruftChecker tests.

Check how scripts/ftpmaster-tools/archive-cruft-check.py works on a
just-published 'ubuntutest' archive.
"""

__metaclass__ = type

import os
import shutil
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import BufferLogger
from lp.soyuz.scripts.ftpmaster import (
    ArchiveCruftChecker,
    ArchiveCruftCheckerError,
    )

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


class TestArchiveCruftChecker(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup the test environment."""
        self.layer.switchDbUser(config.archivepublisher.dbuser)
        self.log = BufferLogger()
        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.breezy_autotest = self.ubuntutest['breezy-autotest']
        self.archive_path = "/var/tmp/archive"
        createTestArchive()

    def tearDown(self):
        """Clean up test environment and remove the test archive."""
        removeTestArchive()

    def testInitializeSuccess(self):
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

        # The 'dist_archive' is an absolute path to the 'dists' section
        # based on the given 'archive_path'.
        self.assertEqual(
            checker.dist_archive,
            '/var/tmp/archive/ubuntutest/dists/breezy-autotest')

        # The 'components' dictionary contains all components selected
        # for the given distroseries organized as:
        #  {$component_name: IComponent, ...}
        for component_name, component in checker.components.iteritems():
            self.assertEqual(component_name, component.name)
        checker_components = sorted(
            [component_name for component_name in checker.components.keys()])
        self.assertEqual(
            checker_components,
            ['main', 'multiverse', 'restricted', 'universe'])

        # The 'components_and_di' lists the relative 'dists' paths
        # for all components subsections of the archive which contain
        # indexes.
        expected = [
            'main',
            'main/debian-installer',
            'multiverse',
            'multiverse/debian-installer',
            'restricted',
            'restricted/debian-installer',
            'universe',
            'universe/debian-installer',
            ]
        self.assertEqual(sorted(checker.components_and_di), expected)

    def testSuiteDistArchive(self):
        """Check if 'dist_archive' path considers pocket correctly."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntutest',
            suite='breezy-autotest-security',
            archive_path=self.archive_path)
        checker.initialize()

        self.assertEqual(
            checker.dist_archive,
            '/var/tmp/archive/ubuntutest/dists/breezy-autotest-security')

    def testInitializeFailure(self):
        """ArchiveCruftCheck initialization failures.

          * An unknown suite;
          * An unknown distribution;
          * The absence of the distribution in the given archive path.
         """
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='miserable',
            archive_path=self.archive_path)
        self.assertRaises(ArchiveCruftCheckerError, checker.initialize)

        checker = ArchiveCruftChecker(
            self.log, distribution_name='foobuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(ArchiveCruftCheckerError, checker.initialize)

        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(ArchiveCruftCheckerError, checker.initialize)
