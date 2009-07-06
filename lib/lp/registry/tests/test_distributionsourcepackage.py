# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for DistributionSourcePackage."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.karma import IKarmaCacheManager
from lp.registry.model.karma import KarmaCategory
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestDistributionSourcePackageFindRelatedArchives(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some gedit sources in main and PPAs."""
        super(TestDistributionSourcePackageFindRelatedArchives, self).setUp()

        self.distribution = getUtility(IDistributionSet)['ubuntutest']

        # Create two PPAs for gedit.
        self.archives = {}
        self.archives['ubuntu-main'] = self.distribution.main_archive
        self.archives['gedit-nightly'] = self.factory.makeArchive(
            name="gedit-nightly", distribution=self.distribution)
        self.archives['gedit-beta'] = self.factory.makeArchive(
            name="gedit-beta", distribution=self.distribution)

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Publish gedit in all three archives.
        self.person_nightly = self.factory.makePerson()
        self.gedit_nightly_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['gedit-nightly'],
            maintainer=self.person_nightly,
            status=PackagePublishingStatus.PUBLISHED)


        self.person_beta = self.factory.makePerson()
        self.gedit_beta_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['gedit-beta'],
            maintainer=self.person_beta,
            status=PackagePublishingStatus.PUBLISHED)
        self.gedit_main_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['ubuntu-main'],
            status=PackagePublishingStatus.PUBLISHED)

        # Save the gedit source package for easy access.
        self.source_package = self.distribution.getSourcePackage('gedit')
        self.soyuz_karma_category = KarmaCategory.byName('soyuz')
        self.karma_cache_manager = getUtility(IKarmaCacheManager)

    def test_default_order_without_karma(self):
        # Returned archives are in archive.id order by default if
        # no soyuz karma is associated with the uploaders.
        related_archives = self.source_package.findRelatedArchives()

        self.assertContentEqual(related_archives, [
            self.archives['gedit-nightly'],
            self.archives['gedit-beta'],
            ])

    def test_order_by_soyuz_package_karma(self):
        # Returned archives are ordered by the soyuz karma of the
        # package uploaders for the particular package

        # Add some karma for the beta PPA uploader and ensure that the
        # beta PPA is first.
        self.layer.switchDbUser('karma')
        self.karma_cache_manager.new(
            200, self.person_beta.id, self.soyuz_karma_category.id,
            distribution_id = self.distribution.id,
            sourcepackagename_id = self.source_package.sourcepackagename.id)
        self.layer.switchDbUser('launchpad')

        related_archives = self.source_package.findRelatedArchives()

        self.assertContentEqual(related_archives, [
            self.archives['gedit-beta'],
            self.archives['gedit-nightly'],
            ])

        # Add more karma for the nightly ppa uploader so that it is
        # displayed first.
        self.layer.switchDbUser('karma')
        self.karma_cache_manager.new(
            201, self.person_nightly.id, self.soyuz_karma_category.id,
            sourcepackagename_id = self.source_package.sourcepackagename.id)
        self.layer.switchDbUser('launchpad')

        related_archives = self.source_package.findRelatedArchives()

        self.assertContentEqual(related_archives, [
            self.archives['gedit-nightly'],
            self.archives['gedit-beta'],
            ])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
