# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Test PackageLocation class."""

import unittest

from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts.ftpmasterbase import (
    PackageLocationError, PackageLocation)


class TestPackageLocation(LaunchpadZopelessTestCase):
    """Test the `PackageLocation` class."""

    def getPackageLocation(self, distribution_name='ubuntu', suite=None):
        return PackageLocation(distribution_name, suite)

    def testSetup(self):
        """Check if PackageLocation` can be properly set up.

        Also check if it raises PackageLocationError on not-found distributions
        and suites.
        """
        location = self.getPackageLocation()
        self.assertEqual(location.distribution.name, 'ubuntu')
        self.assertEqual(location.distroseries.name, 'hoary')
        self.assertEqual(location.pocket.name, 'RELEASE')

        location = self.getPackageLocation(distribution_name='ubuntutest')
        self.assertEqual(location.distribution.name, 'ubuntutest')
        self.assertEqual(location.distroseries.name, 'hoary-test')
        self.assertEqual(location.pocket.name, 'RELEASE')

        location = self.getPackageLocation(suite='warty-security')
        self.assertEqual(location.distribution.name, 'ubuntu')
        self.assertEqual(location.distroseries.name, 'warty')
        self.assertEqual(location.pocket.name, 'SECURITY')

        self.assertRaises(PackageLocationError,
                          self.getPackageLocation, 'beeblebrox')

        self.assertRaises(PackageLocationError,
                          self.getPackageLocation, 'ubuntu', 'beeblebrox')

    def testComparison(self):
        """Check if PackageLocation objects can be compared."""
        location_ubuntu_hoary = self.getPackageLocation()
        location_ubuntu_hoary_again = self.getPackageLocation()
        self.assertEqual(location_ubuntu_hoary, location_ubuntu_hoary_again)

        location_ubuntu_warty_security = self.getPackageLocation(
            suite='warty-security')
        self.assertNotEqual(location_ubuntu_hoary,
                            location_ubuntu_warty_security)

        location_ubuntutest = self.getPackageLocation(
            distribution_name='ubuntutest')
        self.assertNotEqual(location_ubuntu_hoary, location_ubuntutest)

    def testRepresentation(self):
        """Check if PackageLocation is represented correctly."""
        location_ubuntu_hoary = self.getPackageLocation()
        self.assertEqual(str(location_ubuntu_hoary), 'ubuntu/hoary/RELEASE')

        location_ubuntu_warty_security = self.getPackageLocation(
            suite='warty-security')
        self.assertEqual(str(location_ubuntu_warty_security),
                         'ubuntu/warty/SECURITY')

        location_ubuntutest = self.getPackageLocation(
            distribution_name='ubuntutest')
        self.assertEqual(str(location_ubuntutest),
                         'ubuntutest/hoary-test/RELEASE')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
