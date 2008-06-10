# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Test PackageLocation class."""

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces import ArchivePurpose, IComponentSet
from canonical.launchpad.components.packagelocation import (
    PackageLocationError, build_package_location)
from canonical.testing import LaunchpadZopelessLayer


class TestPackageLocation(unittest.TestCase):
    """Test the `PackageLocation` class."""
    layer = LaunchpadZopelessLayer

    def getPackageLocation(self, distribution_name='ubuntu', suite=None,
                           purpose=None, person_name=None):
        """Use a helper method to setup a `PackageLocation` object."""
        return build_package_location(
            distribution_name, suite, purpose, person_name)

    def testSetupLocationForPRIMARY(self):
        """`PackageLocation` for PRIMARY archives."""
        location = self.getPackageLocation()
        self.assertEqual(location.distribution.name, 'ubuntu')
        self.assertEqual(location.distroseries.name, 'hoary')
        self.assertEqual(location.pocket.name, 'RELEASE')
        self.assertEqual(location.archive.title,
                         'Primary Archive for Ubuntu Linux')

    def testSetupLocationForPPA(self):
        """`PackageLocation` for PPA archives."""
        location = self.getPackageLocation(purpose=ArchivePurpose.PPA,
                                           person_name='cprov')
        self.assertEqual(location.distribution.name, 'ubuntu')
        self.assertEqual(location.distroseries.name, 'hoary')
        self.assertEqual(location.pocket.name, 'RELEASE')
        self.assertEqual(location.archive.title,
                         'PPA for Celso Providelo')

    def testSetupLocationForPARTNER(self):
        """`PackageLocation` for PARTNER archives."""
        location = self.getPackageLocation(purpose=ArchivePurpose.PARTNER)
        self.assertEqual(location.distribution.name, 'ubuntu')
        self.assertEqual(location.distroseries.name, 'hoary')
        self.assertEqual(location.pocket.name, 'RELEASE')
        self.assertEqual(location.archive.title,
                         'Partner Archive for Ubuntu Linux')

    def testSetupLocationUnknownDistribution(self):
        """`PackageLocationError` is raised on unknown distribution."""
        self.assertRaises(
            PackageLocationError,
            self.getPackageLocation,
            distribution_name='beeblebrox')

    def testSetupLocationUnknownSuite(self):
        """`PackageLocationError` is raised on unknown suite."""
        self.assertRaises(
            PackageLocationError,
            self.getPackageLocation,
            suite='beeblebrox')

    def testSetupLocationUnknownPerson(self):
        """`PackageLocationError` is raised on unknown person."""
        self.assertRaises(
            PackageLocationError,
            self.getPackageLocation,
            purpose=ArchivePurpose.PPA,
            person_name='beeblebrox')

    def testSetupLocationUnknownPPA(self):
        """`PackageLocationError` is raised on unknown PPA."""
        self.assertRaises(
            PackageLocationError,
            self.getPackageLocation,
            purpose=ArchivePurpose.PPA,
            person_name='kiko')

    def testSetupLocationPPANotMatchingDistribution(self):
        """`PackageLocationError` is raised when PPA does not match the
        distribution."""
        self.assertRaises(
            PackageLocationError,
            self.getPackageLocation,
            distribution_name='ubuntutest',
            purpose=ArchivePurpose.PPA,
            person_name='cprov')

    def testComparison(self):
        """Check if PackageLocation objects can be compared."""
        location_ubuntu_hoary = self.getPackageLocation()
        location_ubuntu_hoary_again = self.getPackageLocation()
        self.assertEqual(location_ubuntu_hoary, location_ubuntu_hoary_again)

        self.assertTrue(location_ubuntu_hoary.component is None)
        self.assertTrue(location_ubuntu_hoary_again.component is None)

        universe = getUtility(IComponentSet)['universe']
        restricted = getUtility(IComponentSet)['restricted']

        location_ubuntu_hoary.component = universe
        self.assertNotEqual(location_ubuntu_hoary, location_ubuntu_hoary_again)

        location_ubuntu_hoary_again.component = universe
        self.assertEqual(location_ubuntu_hoary, location_ubuntu_hoary_again)

        location_ubuntu_hoary.component = restricted
        self.assertNotEqual(location_ubuntu_hoary, location_ubuntu_hoary_again)

        location_ubuntu_warty_security = self.getPackageLocation(
            suite='warty-security')
        self.assertNotEqual(location_ubuntu_hoary,
                            location_ubuntu_warty_security)

        location_ubuntutest = self.getPackageLocation(
            distribution_name='ubuntutest')
        self.assertNotEqual(location_ubuntu_hoary, location_ubuntutest)

        location_cprov_ppa = self.getPackageLocation(
            distribution_name='ubuntu', purpose=ArchivePurpose.PPA,
            person_name='cprov')
        self.assertNotEqual(location_cprov_ppa, location_ubuntutest)

        location_ubuntu_partner = self.getPackageLocation(
            distribution_name='ubuntu', purpose=ArchivePurpose.PARTNER)
        self.assertNotEqual(location_ubuntu_partner, location_cprov_ppa)

    def testRepresentation(self):
        """Check if PackageLocation is represented correctly."""
        location_ubuntu_hoary = self.getPackageLocation()
        self.assertEqual(str(location_ubuntu_hoary),
                         'Primary Archive for Ubuntu Linux: hoary-RELEASE')

        location_ubuntu_warty_security = self.getPackageLocation(
            suite='warty-security')
        self.assertEqual(str(location_ubuntu_warty_security),
                         'Primary Archive for Ubuntu Linux: warty-SECURITY')

        location_ubuntutest = self.getPackageLocation(
            distribution_name='ubuntutest')
        self.assertEqual(
            str(location_ubuntutest),
            'Primary Archive for Ubuntu Test: hoary-test-RELEASE')

        location_cprov_ppa = self.getPackageLocation(
            distribution_name='ubuntu', purpose=ArchivePurpose.PPA,
            person_name='cprov')
        self.assertEqual(
            str(location_cprov_ppa),
            'cprov: hoary-RELEASE')

        location_ubuntu_partner = self.getPackageLocation(
            distribution_name='ubuntu', purpose=ArchivePurpose.PARTNER)
        self.assertEqual(
            str(location_ubuntu_partner),
            'Partner Archive for Ubuntu Linux: hoary-RELEASE')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
