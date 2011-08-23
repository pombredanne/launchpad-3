# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for DistributionSourcePackage."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.model.karma import KarmaTotalCache
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestDistributionSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_dsp_with_no_series_summary(self):
        distribution_set = getUtility(IDistributionSet)

        distribution = distribution_set.new(name='wart',
            displayname='wart', title='wart', description='lots of warts',
            summary='lots of warts', domainname='wart.dumb',
            members=self.factory.makeTeam(), owner=self.factory.makePerson(),
            registrant=self.factory.makePerson())
        naked_distribution = removeSecurityProxy(distribution)
        self.factory.makeSourcePackage(distroseries=distribution)
        dsp = naked_distribution.getSourcePackage(name='pmount')
        self.assertEqual(None, dsp.summary)


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
            creator=self.person_nightly,
            status=PackagePublishingStatus.PUBLISHED)

        self.person_beta = self.factory.makePerson()
        self.gedit_beta_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['gedit-beta'],
            creator=self.person_beta,
            status=PackagePublishingStatus.PUBLISHED)
        self.gedit_main_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['ubuntu-main'],
            status=PackagePublishingStatus.PUBLISHED)

        # Save the gedit source package for easy access.
        self.source_package = self.distribution.getSourcePackage('gedit')

        # Add slightly more soyuz karma for person_nightly for this package.
        transaction.commit()
        self.layer.switchDbUser('karma')
        self.person_beta_karma = KarmaTotalCache(
            person=self.person_beta, karma_total=200)
        self.person_nightly_karma = KarmaTotalCache(
            person=self.person_nightly, karma_total=201)
        transaction.commit()
        self.layer.switchDbUser('launchpad')

    def test_order_by_soyuz_package_karma(self):
        # Returned archives are ordered by the soyuz karma of the
        # package uploaders for the particular package

        related_archives = self.source_package.findRelatedArchives()
        related_archive_names = [
            archive.name for archive in related_archives]

        self.assertEqual(related_archive_names, [
            'gedit-nightly',
            'gedit-beta',
            ])

        # Update the soyuz karma for person_beta for this package so that
        # it is greater than person_nightly's.
        self.layer.switchDbUser('karma')
        self.person_beta_karma.karma_total = 202
        transaction.commit()
        self.layer.switchDbUser('launchpad')

        related_archives = self.source_package.findRelatedArchives()
        related_archive_names = [
            archive.name for archive in related_archives]

        self.assertEqual(related_archive_names, [
            'gedit-beta',
            'gedit-nightly',
            ])

    def test_require_package_karma(self):
        # Only archives where the related package was created by a person
        # with the required soyuz karma for this package.

        related_archives = self.source_package.findRelatedArchives(
            required_karma=201)
        related_archive_names = [
            archive.name for archive in related_archives]

        self.assertEqual(related_archive_names, ['gedit-nightly'])

    def test_development_version(self):
        # IDistributionSourcePackage.development_version is the ISourcePackage
        # for the current series of the distribution.
        dsp = self.factory.makeDistributionSourcePackage()
        series = self.factory.makeDistroSeries(distribution=dsp.distribution)
        self.assertEqual(series, dsp.distribution.currentseries)
        development_version = dsp.distribution.currentseries.getSourcePackage(
            dsp.sourcepackagename)
        self.assertEqual(development_version, dsp.development_version)

    def test_development_version_no_current_series(self):
        # IDistributionSourcePackage.development_version is the ISourcePackage
        # for the current series of the distribution.
        dsp = self.factory.makeDistributionSourcePackage()
        currentseries = dsp.distribution.currentseries
        # The current series is None by default.
        self.assertIs(None, currentseries)
        self.assertEqual(None, dsp.development_version)

    def test_does_not_include_copied_packages(self):
        # Packages that have been copied rather than uploaded are not
        # included when determining related archives.

        # Ensure that the gedit package in gedit-nightly was originally
        # uploaded to gedit-beta (ie. copied from there).
        gedit_release = self.gedit_nightly_src_hist.sourcepackagerelease
        gedit_release.upload_archive = self.archives['gedit-beta']

        related_archives = self.source_package.findRelatedArchives()
        related_archive_names = [
            archive.name for archive in related_archives]

        self.assertEqual(related_archive_names, ['gedit-beta'])
