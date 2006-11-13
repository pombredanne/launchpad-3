# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Tests for publisher class."""

__metaclass__ = type

import unittest
import os

from canonical.launchpad.tests.test_publishing import TestNativePublishingBase
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistributionReleaseStatus)


class TestPublisher(TestNativePublishingBase):

    def assertDirtyPocketsContents(self, expected, dirty_pockets):
        contents = [(str(dr_name), pocket.name) for dr_name, pocket in
                    dirty_pockets]
        self.assertEqual(expected, contents)

    def testInstantiate(self):
        """Publisher should be instantiatable"""
        from canonical.archivepublisher.publishing import Publisher
        Publisher(self.logger, self.config, self.disk_pool, self.ubuntutest)

    def testPublishing(self):
        """Test the non-careful publishing procedure.

        With one PENDING record, respective pocket *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            "foo", "main", "foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING)

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # file got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testPublishingSpecificDistroRelease(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific distrorelease.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            allowed_suites=[('hoary-test', PackagePublishingPocket.RELEASE)])

        pub_source = self.getPubSource(
            "foo", "main", "foo.dsc", filecontent='foo',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE,
            distrorelease=self.ubuntutest['breezy-autotest'])
        pub_source2 = self.getPubSource(
            "baz", "main", "baz.dsc", filecontent='baz',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.RELEASE,
            distrorelease=self.ubuntutest['hoary-test'])

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('hoary-test', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

    def testPublishingSpecificPocket(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific pocket.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            allowed_suites=[('breezy-autotest',
                             PackagePublishingPocket.UPDATES)])

        self.ubuntutest['breezy-autotest'].releasestatus = (
            DistributionReleaseStatus.CURRENT)

        pub_source = self.getPubSource(
            "foo", "main", "foo.dsc", filecontent='foo',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.UPDATES,
            distrorelease=self.ubuntutest['breezy-autotest'])
        pub_source2 = self.getPubSource(
            "baz", "main", "baz.dsc", filecontent='baz',
            status=PackagePublishingStatus.PENDING,
            pocket=PackagePublishingPocket.BACKPORTS,
            distrorelease=self.ubuntutest['breezy-autotest'])

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'UPDATES')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PENDING)

    def testNonCarefulPublishing(self):
        """Test the non-careful publishing procedure.

        With one PUBLISHED record, no pockets *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            "foo", "main", "foo.dsc", status=PackagePublishingStatus.PUBLISHED)

        # a new non-careful publisher won't find anything to publish, thus
        # no pockets will be *dirtied*.
        publisher.A_publish(False)

        self.assertDirtyPocketsContents([], publisher.dirty_pockets)
        # nothing got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

    def testCarefulPublishing(self):
        """Test the careful publishing procedure.

        With one PUBLISHED record, pocket gets *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            "foo", "main", "foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED)

        # A careful publisher run will re-publish the PUBLISHED records,
        # then we will have a corresponding dirty_pocket entry.
        publisher.A_publish(True)

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        # file got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

