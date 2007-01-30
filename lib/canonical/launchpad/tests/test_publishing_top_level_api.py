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


    def testPublicationLookUpForUnreleasedDistroRelease(self):
        """Source publishing record lookup for a released DistroRelease.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroRelease when it is still in development, 'unreleased'.
        """
        pub_pending_release = self.getPubSource(
            sourcename='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_published_release = self.getPubSource(
            sourcename='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_pending_updates = self.getPubSource(
            sourcename='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # Usual publication procedure for a distrorelease in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unsusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])


    def testPublicationLookUpForReleasedDistroRelease(self):
        """Source publishing record lookup for a released DistroRelease.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroRelease when it is not in development anymore, i.e.,
        'released'.
        """
        pub_pending_release = self.getPubSource(
            sourcename='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_published_release = self.getPubSource(
            sourcename='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_pending_updates = self.getPubSource(
            sourcename='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # Release 'breezy-autotest'.
        self.breezy_autotest.releasestatus = DistributionReleaseStatus.CURRENT

        # Since the distro is published, nothing is returned because
        # RELEASE pocket is ignored, in both modes, careful or not.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # XXX cprov 20070105: it means that "careful" mode is useless for
        # rebuilding released archives.
        # This is quite right, IMHO, since republication of a released
        # archive will, obviously contain new timestamps, which would freak
        # mirrors/clients out.
        # At the end, "careful" mode is such a gross hack.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)

        # Publications targeted to other pockets than RELEASE are
        # still reachable.
        pub_records = self.breezy_autotest.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

    def testPublicationLookUpForUnreleasedDistroArchRelease(self):
        """Binary publishing record lookup for a unreleased DAR.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroArchRelease when it is still in developement, i.e.,
        'unreleased'.
        """
        pub_pending_release = self.getPubBinary(
            binaryname='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_published_release = self.getPubBinary(
            binaryname='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_pending_updates = self.getPubBinary(
            binaryname='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # Usual publication procedure for a distrorelease in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unsusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])

    def testPublicationLookUpForReleasedDistroArchRelease(self):
        """Binary publishing record lookup for a released DistroArchRelease.

        Check if the IPublishing.getPendingPubliations() works properly for
        a DistroArchRelease when it is not in development anymore, i.e.,
        'released'.
        """
        pub_pending_release = self.getPubBinary(
            binaryname='first',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE)

        pub_published_release = self.getPubBinary(
            binaryname='second',
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        pub_pending_updates = self.getPubBinary(
            binaryname='third',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES)

        # Release 'breezy-autotest'
        self.breezy_autotest.releasestatus = DistributionReleaseStatus.CURRENT
        # XXX cprov 20070117: why do I need to commit here ?
        # A similar operation is done in line 136 of this file w/o this
        # requirement.
        self.layer.commit()

        # Since the distro is published, nothing is returned because
        # RELEASE pocket is ignored, in both modes, careful or not.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # XXX cprov 20070105: it means that "careful" mode is useless for
        # rebuilding released archives.
        # This is quite right, IMHO, since republication of a released
        # archive will, obviously contain new timestamps, which would freak
        # mirrors/clients out.
        # At the end, "careful" mode is such a gross hack.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)

        # Publications targeted to other pockets than RELEASE are
        # still reachable.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
