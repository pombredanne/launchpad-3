# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test top-level publication API in Soyuz."""

import os
from unittest import TestLoader

from canonical.launchpad.tests.test_publishing import TestNativePublishingBase

from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingStatus,
    DistributionReleaseStatus)

class TestIPublishingAPI(TestNativePublishingBase):

    def testPublishDistroRelease(self):
        """Top level publication for IDistroRelease.

        Source and Binary get published.
        """
        pub_source = self.getPubSource(filecontent="Hello")
        pub_bin = self.getPubBinary(
            filecontent="World", pub_source=pub_source)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.layer.txn.commit()

        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        foo_dsc = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_dsc).read().strip(),'Hello')

        foo_deb = "%s/main/f/foo/foo-bin.deb" % self.pool_dir
        self.assertEqual(open(foo_deb).read().strip(), 'World')

    def testPublishDistroArchRelease(self):
        """Top level publication for IDistroArchRelease.

        Only binary gets published.
        """
        pub_source = self.getPubSource(filecontent="Hello")
        pub_bin = self.getPubBinary(filecontent="World", pub_source=pub_source)

        self.breezy_autotest_i386.publish(
            self.disk_pool, self.logger,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.layer.txn.commit()

        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        foo_dsc = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(os.path.exists(foo_dsc), False)

        foo_deb = "%s/main/f/foo/foo-bin.deb" % self.pool_dir
        self.assertEqual(open(foo_deb).read().strip(), 'World')


    def testGetPendingPublicationsForDistroRelease(self):
        """getPendingPublication should return only the relevant records.

        Results will be restricted to the given 'pocket', additionally,
        RELEASE pocket will be automatically excluded for released/stable
        distroreleases (see IDistroRelease.isUnstable).

        'Careful' mode, will consider also published records.
        """
        # fill publishing tables:
        pub_source1 = self.getPubSource(
            sourcename='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_source2 = self.getPubSource(
            sourcename='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_source3 = self.getPubSource(
            sourcename='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # only "first" is return for RELEASE & non-careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_source1.id], [pub.id for pub in pub_records])

        # only "third" is returned for UPDATES & non-careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_source3.id], [pub.id for pub in pub_records])

        # nothing is returned for BACKPORTS & non-careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # "second" and "first" are returned for RELEASE & careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_source2.id, pub_source1.id], [pub.id for pub in pub_records])

        # let's release breezy-autotest 
        self.breezy_autotest.releasestatus = DistributionReleaseStatus.CURRENT

        # nothing is returned for RELEASE & non-careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # "third" is returned for UPDATES & non-careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_source3.id], [pub.id for pub in pub_records])

        # nothing is returned for RELEASE & careful
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)
        # XXX cprov 20070105: it means that "careful" mode is useless for
        # rebuilding released archives.
        # This is quite right, IMHO, since republication of a released
        # archive will, obviously contain new timestamps, which would freak
        # mirrors/clients out.
        # At the end, "careful" mode is such a gross hack.


    def testGetPendingPublicationsForDistroArchRelease(self):
        """Exactly the same as it works for DistroRelease.

        Except that it consider binary publications, instead of sources.
        """
        # fill publishing tables:
        pub_binary1 = self.getPubBinary(
            binaryname='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_binary2 = self.getPubBinary(
            binaryname='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_binary3 = self.getPubBinary(
            binaryname='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # only "first" is return for RELEASE & non-careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_binary1.id], [pub.id for pub in pub_records])

        # only "third" is returned for UPDATES & non-careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_binary3.id], [pub.id for pub in pub_records])

        # nothing is returned for BACKPORTS & non-careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # "second" and "first" are returned for RELEASE & careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_binary2.id, pub_binary1.id], [pub.id for pub in pub_records])

        # let's release breezy-autotest
        self.breezy_autotest.releasestatus = DistributionReleaseStatus.CURRENT
        self.layer.txn.commit()

        # nothing is returned for RELEASE & non-careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # "third" is returned for UPDATES & non-careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_binary3.id], [pub.id for pub in pub_records])

        # nothing is returned for RELEASE & careful
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)
        # XXX: see above.


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
