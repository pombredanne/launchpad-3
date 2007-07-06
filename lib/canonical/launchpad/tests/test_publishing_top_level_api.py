# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test top-level publication API in Soyuz."""

import os
from unittest import TestLoader

from canonical.launchpad.tests.test_publishing import TestNativePublishingBase

from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingStatus,
    DistroSeriesStatus)

class TestIPublishingAPI(TestNativePublishingBase):

    def _createLinkedPublication(self, name, pocket):
        """Create and return a linked pair of source and binary publications."""
        pub_source = self.getPubSource(
            sourcename=name, filecontent="Hello", pocket=pocket)

        binaryname = '%s-bin' % name
        pub_bin = self.getPubBinary(
            binaryname=binaryname, filecontent="World",
            pub_source=pub_source, pocket=pocket)

        return (pub_source, pub_bin)

    def _createDefaulSourcePublications(self):
        """Create and return default source publications.

        See TestNativePublishingBase.getPubSource for more information.

        It creates the following publications in brezzy-autotest context:

         * a PENDING publication for RELEASE pocket;
         * a PUBLISHED publication for RELEASE pocket;
         * a PENDING publication for UPDATES pocket;

        Returns the respective ISPPH objects as a tuple.
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

        return (pub_pending_release, pub_published_release, pub_pending_updates)

    def _createDefaulBinaryPublications(self):
        """Create and return default binary publications.

        See TestNativePublishingBase.getPubBinary for more information.

        It creates the following publications in brezzy-autotest context:

         * a PENDING publication for RELEASE pocket;
         * a PUBLISHED publication for RELEASE pocket;
         * a PENDING publication for UPDATES pocket;

        Returns the respective IBPPH objects as a tuple.
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

        return (pub_pending_release, pub_published_release, pub_pending_updates)

    def testPublishUnstableDistroSeries(self):
        """Top level publication for IDistroSeries in 'unstable' states.

        Source and Binary publications to pocket RELEASE get PUBLISHED.
        Source and Binary publications to pocket UPDATES (any post-release,
        in fact) are still PENDING.

        Note that it also tests IDistroArchSeries.publish() API, since it's
        invoked/chained inside IDistroSeries.publish().
        """
        self.assertEqual(
            self.breezy_autotest.status, DistroSeriesStatus.EXPERIMENTAL)
        self.assertEqual(
            self.breezy_autotest.isUnstable(), True)

        # RELEASE pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='foo', pocket=PackagePublishingPocket.RELEASE)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.layer.txn.commit()

        # PUBLISHED in database.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        # PUBLISHED on disk.
        foo_dsc = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_dsc).read().strip(),'Hello')

        foo_deb = "%s/main/f/foo/foo-bin.deb" % self.pool_dir
        self.assertEqual(open(foo_deb).read().strip(), 'World')

        # UPDATES (post-release) pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='bar', pocket=PackagePublishingPocket.UPDATES)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.layer.txn.commit()

        # The publications to pocket UPDATES were ignored.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PENDING)

    def testPublishStableDistroSeries(self):
        """Top level publication for IDistroSeries in 'stable' states.

        Source and Binary publications to pocket RELEASE are ignored.
        Source and Binary publications to pocket UPDATES get PUBLISHED.
        """
        # Release ubuntu/breezy-autotest.
        self.breezy_autotest.status = DistroSeriesStatus.CURRENT
        self.layer.commit()

        self.assertEqual(
            self.breezy_autotest.status, DistroSeriesStatus.CURRENT)
        self.assertEqual(
            self.breezy_autotest.isUnstable(), False)

        # UPDATES (post-release) pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='bar', pocket=PackagePublishingPocket.UPDATES)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.layer.txn.commit()

        # PUBLISHED in database.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        # PUBLISHED on disk.
        bar_dsc = "%s/main/b/bar/bar.dsc" % self.pool_dir
        self.assertEqual(open(bar_dsc).read().strip(),'Hello')

        bar_deb = "%s/main/b/bar/bar-bin.deb" % self.pool_dir
        self.assertEqual(open(bar_deb).read().strip(), 'World')

        # RELEASE pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='foo', pocket=PackagePublishingPocket.RELEASE)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.layer.txn.commit()

        # The publications to pocket RELEASE where ignored.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PENDING)

    def testPublishFrozenDistroSeries(self):
        """Top level publication for IDistroSeries in FROZEN state.

        Source and Binary publications to pocket RELEASE get PUBLISHED.
        Source and Binary publications to pocket UPDATES get PUBLISHED.
        """
        # Release ubuntu/breezy-autotest.
        self.breezy_autotest.status = DistroSeriesStatus.FROZEN
        self.layer.commit()

        self.assertEqual(
            self.breezy_autotest.status, DistroSeriesStatus.FROZEN)
        self.assertEqual(
            self.breezy_autotest.isUnstable(), True)

        # UPDATES (post-release) pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='bar', pocket=PackagePublishingPocket.UPDATES)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.layer.txn.commit()

        # PUBLISHED in database.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        # PUBLISHED on disk.
        bar_dsc = "%s/main/b/bar/bar.dsc" % self.pool_dir
        self.assertEqual(open(bar_dsc).read().strip(),'Hello')

        bar_deb = "%s/main/b/bar/bar-bin.deb" % self.pool_dir
        self.assertEqual(open(bar_deb).read().strip(), 'World')

        # RELEASE pocket.
        pub_source, pub_bin = self._createLinkedPublication(
            name='foo', pocket=PackagePublishingPocket.RELEASE)

        self.breezy_autotest.publish(
            self.disk_pool, self.logger,
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.layer.txn.commit()

        # The publications to pocket RELEASE also get PUBLISHED.
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_bin.status, PackagePublishingStatus.PUBLISHED)

        # PUBLISHED on disk.
        foo_dsc = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(bar_dsc).read().strip(),'Hello')

        foo_deb = "%s/main/f/foo/foo-bin.deb" % self.pool_dir
        self.assertEqual(open(foo_deb).read().strip(), 'World')

    def testPublicationLookUpForUnstableDistroSeries(self):
        """Source publishing record lookup for a unstable DistroSeries.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroSeries when it is still in development, 'unreleased'.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulSourcePublications())

        # Usual publication procedure for a distroseries in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])

    def testPublicationLookUpForStableDistroSeries(self):
        """Source publishing record lookup for a stable/released DistroSeries.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroSeries when it is not in development anymore, i.e.,
        'released'.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulSourcePublications())

        # Release 'breezy-autotest'.
        self.breezy_autotest.status = DistroSeriesStatus.CURRENT

        # Since the distroseries is stable, nothing is returned because
        # RELEASE pocket is ignored, in both modes, careful or not.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
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
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)

        # Publications targeted to other pockets than RELEASE are
        # still reachable.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

    def testPublicationLookUpForFrozenDistroSeries(self):
        """Source publishing record lookup for a frozen DistroSeries.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroSeries when it is in FROZEN state.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulSourcePublications())
        # Freeze 'breezy-autotest'.
        self.breezy_autotest.status = DistroSeriesStatus.FROZEN
        self.layer.commit()

        # Usual publication procedure for a distroseries in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])

    def testPublicationLookUpForUnstableDistroArchSeries(self):
        """Binary publishing record lookup for a unstable DistroArchSeries.

        Check if the IPublishing.getPendingPubliations() works properly
        for a DistroArchSeries when it is still in DEVELOPMENT, i.e.,
        'unstable'.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulBinaryPublications())
        self.layer.commit()

        # Usual publication procedure for a distroseries in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])

    def testPublicationLookUpForStableDistroArchSeries(self):
        """Binary publishing record lookup for stable/released DistroArchSeries.

        Check if the IPublishing.getPendingPubliations() works properly for
        a DistroArchSeries when it is not in development anymore, i.e.,
        'released'.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulBinaryPublications())

        # Release 'breezy-autotest'
        self.breezy_autotest.status = DistroSeriesStatus.CURRENT
        self.layer.commit()

        # Since the distroseries is stable, nothing is returned because
        # RELEASE pocket is ignored, in both modes, careful or not.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
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
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 0)

        # Publications targeted to other pockets than RELEASE are
        # still reachable.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

    def testPublicationLookUpForFrozenDistroArchSeries(self):
        """Binary publishing record lookup for a frozen DistroArchSeries.

        Check if the IPublishing.getPendingPubliations() works properly for
        a DistroArchSeries when it is frozen state.
        """
        pub_pending_release, pub_published_release, pub_pending_updates = (
            self._createDefaulBinaryPublications())
        # Freeze 'breezy-autotest'
        self.breezy_autotest.status = DistroSeriesStatus.FROZEN
        self.layer.commit()

        # Usual publication procedure for a distroseries in development
        # state only 'pending' publishing records for pocket RELEASE
        # are published.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_release.id], [pub.id for pub in pub_records])

        # This step is unusual but checks if the pocket restriction also
        # work for other pockets than the RELEASE.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            is_careful=False)
        self.assertEqual(pub_records.count(), 1)
        self.assertEqual(
            [pub_pending_updates.id], [pub.id for pub in pub_records])

        # Restricting to a pocket with no publication returns an
        # empty SQLResult.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.BACKPORTS,
            is_careful=False)
        self.assertEqual(pub_records.count(), 0)

        # Using the 'careful' mode results in the consideration
        # of every 'pending' and 'published' records present in
        # the given pocket.
        pub_records = self.breezy_autotest_i386.getPendingPublications(
            archive=self.breezy_autotest.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            is_careful=True)
        self.assertEqual(pub_records.count(), 2)
        self.assertEqual(
            [pub_published_release.id, pub_pending_release.id],
            [pub.id for pub in pub_records])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
