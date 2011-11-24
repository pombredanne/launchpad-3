# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions/classes for Soyuz tests."""

__metaclass__ = type

__all__ = [
    'SoyuzTestHelper',
    'TestPackageDiffsBase',
    ]

import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.ftests import (
    import_public_test_keys,
    )
from canonical.launchpad.testing.fakepackager import FakePackager
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.packagediff import IPackageDiffSet
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.sampledata import (
    BUILDD_ADMIN_USERNAME,
    CHROOT_LIBRARYFILEALIAS,
    I386_ARCHITECTURE_NAME,
    LAUNCHPAD_DBUSER_NAME,
    UBUNTU_DISTRIBUTION_NAME,
    WARTY_DISTROSERIES_NAME,
    WARTY_UPDATES_SUITE_NAME,
    )


class SoyuzTestHelper:
    """Helper class to support easier tests in Soyuz component."""

    def __init__(self):
        self.ubuntu = getUtility(IDistributionSet)[UBUNTU_DISTRIBUTION_NAME]
        self.cprov_archive = getUtility(
            IPersonSet).getByName(BUILDD_ADMIN_USERNAME).archive

    @property
    def sample_publishing_data(self):
        """Return a list of triples as (status, archive, pocket).

        Returns the following triples (in this order):

         1. ubuntu/PRIMARY, PENDING, RELEASE;
         2. ubuntu/PRIMARY, PUBLISHED, RELEASE;
         3. ubuntu/PRIMARY, PENDING, UPDATES;
         4. ubuntu/PRIMARY, PUBLISHED, PROPOSED;
         5. ubuntu/cprov PPA, PENDING, RELEASE;
         6. ubuntu/cprov PPA, PUBLISHED, RELEASE;
         7. ubuntu/cprov PPA, PENDING, UPDATES;
         8. ubuntu/cprov PPA, PUBLISHED, PROPOSED;
        """
        return [
            (PackagePublishingStatus.PENDING, self.ubuntu.main_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PUBLISHED, self.ubuntu.main_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PENDING, self.ubuntu.main_archive,
             PackagePublishingPocket.UPDATES),
            (PackagePublishingStatus.PUBLISHED, self.ubuntu.main_archive,
             PackagePublishingPocket.PROPOSED),
            (PackagePublishingStatus.PENDING, self.cprov_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PUBLISHED, self.cprov_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PENDING, self.cprov_archive,
             PackagePublishingPocket.UPDATES),
            (PackagePublishingStatus.PUBLISHED, self.cprov_archive,
             PackagePublishingPocket.PROPOSED),
            ]

    def createPublishingForDistroSeries(self, sourcepackagerelease,
                                        distroseries):
        """Return a list of `SourcePackagePublishingHistory`.

        The publishing records are created according the given
        `SourcePackageRelease` and `DistroSeries` for all
        (status, archive, pocket) returned from `sample_publishing_data`.
        """
        sample_pub = []
        for status, archive, pocket in self.sample_publishing_data:
            pub = SourcePackagePublishingHistory(
                sourcepackagerelease=sourcepackagerelease,
                distroseries=distroseries,
                component=sourcepackagerelease.component,
                section=sourcepackagerelease.section,
                status=status,
                archive=archive,
                pocket=pocket)
            # Flush the object changes into DB do guarantee stable database
            # ID order as expected in the callsites.
            sample_pub.append(pub)
        return sample_pub

    def createPublishingForDistroArchSeries(self, binarypackagerelease,
                                            distroarchseries):
        """Return a list of `BinaryPackagePublishingHistory`.

        The publishing records are created according the given
        `BinaryPackageRelease` and `DistroArchSeries` for all
        (status, archive, pocket) returned from `sample_publishing_data`.
        """
        sample_pub = []
        for status, archive, pocket in self.sample_publishing_data:
            pub = BinaryPackagePublishingHistory(
                binarypackagerelease=binarypackagerelease,
                distroarchseries=distroarchseries,
                component=binarypackagerelease.component,
                section=binarypackagerelease.section,
                priority=binarypackagerelease.priority,
                status=status,
                archive=archive,
                pocket=pocket)
            # Flush the object changes into DB do guarantee stable database
            # ID order as expected in the callsites.
            sample_pub.append(pub)
        return sample_pub

    def checkPubList(self, expected, given):
        """Check if the given publication list matches the expected one.

        Return True if the lists matches, otherwise False.
        """
        return [p.id for p in expected] == [r.id for r in given]


class TestPackageDiffsBase(unittest.TestCase):
    """Base class facilitating tests related to package diffs."""
    layer = LaunchpadZopelessLayer
    dbuser = config.uploader.dbuser

    def setUp(self):
        """Setup proper DB connection and contents for tests

        Connect to the DB as the 'uploader' user (same user used in the
        script), upload the test packages (see `uploadTestPackages`) and
        commit the transaction.

        Store the `FakePackager` object used in the test uploads as `packager`
        so the tests can reuse it if necessary.
        """
        with dbuser(LAUNCHPAD_DBUSER_NAME):
            fake_chroot = LibraryFileAlias.get(CHROOT_LIBRARYFILEALIAS)
            ubuntu = getUtility(IDistributionSet).getByName(
                UBUNTU_DISTRIBUTION_NAME)
            warty = ubuntu.getSeries(WARTY_DISTROSERIES_NAME)
            warty[I386_ARCHITECTURE_NAME].addOrUpdateChroot(fake_chroot)

        self.packager = self.uploadTestPackages()
        self.layer.txn.commit()

    def uploadTestPackages(self):
        """Upload packages for testing `PackageDiff` generation script.

        Upload zeca_1.0-1 and zeca_1.0-2 sources, so a `PackageDiff` between
        them is created.

        Assert there is not pending `PackageDiff` in the DB before uploading
        the package and also assert that there is one after the uploads.

        :return: the FakePackager object used to generate and upload the test,
            packages, so the tests can upload subsequent version if necessary.
        """
        # No pending PackageDiff available in sampledata.
        self.assertEqual(self.getPendingDiffs().count(), 0)

        import_public_test_keys()
        # Use FakePackager to upload a base package to ubuntu.
        packager = FakePackager(
            'zeca', '1.0', 'foo.bar@canonical.com-passwordless.sec')
        packager.buildUpstream()
        packager.buildSource()
        packager.uploadSourceVersion('1.0-1', suite=WARTY_UPDATES_SUITE_NAME)

        # Upload a new version of the source, so a PackageDiff can
        # be created.
        packager.buildVersion('1.0-2', changelog_text="cookies")
        packager.buildSource(include_orig=False)
        packager.uploadSourceVersion('1.0-2', suite=WARTY_UPDATES_SUITE_NAME)

        # Check if there is exactly one pending PackageDiff record and
        # It's the one we have just created.
        self.assertEqual(self.getPendingDiffs().count(), 1)

        return packager

    def getPendingDiffs(self):
        """Pending `PackageDiff` available."""
        return getUtility(IPackageDiffSet).getPendingDiffs()
