# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive features."""

from datetime import datetime
import pytz
import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.binarypackagerelease import BinaryPackageFormat
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory

class TestGetPublicationsInArchive(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestGetPublicationsInArchive, self).setUp()

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

        # Publish gedit in all three archives, but with different
        # upload dates.
        self.gedit_nightly_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['gedit-nightly'],
            date_uploaded=datetime(2010, 12 ,1, tzinfo=pytz.UTC),
            status=PackagePublishingStatus.PUBLISHED)
        self.gedit_beta_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['gedit-beta'],
            date_uploaded=datetime(2010, 11, 30, tzinfo=pytz.UTC),
            status=PackagePublishingStatus.PUBLISHED)
        self.gedit_main_src_hist = self.publisher.getPubSource(
            sourcename="gedit", archive=self.archives['ubuntu-main'],
            date_uploaded=datetime(2010, 12, 30, tzinfo=pytz.UTC),
            status=PackagePublishingStatus.PUBLISHED)

        # Save the archive utility for easy access, as well as the gedit
        # source package name.
        self.archive_set = getUtility(IArchiveSet)
        spr = self.gedit_main_src_hist.sourcepackagerelease
        self.gedit_name = spr.sourcepackagename

    def testReturnsAllPublishedPublications(self):
        # Returns all currently published publications for archives
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values(),
            distribution=self.distribution)
        num_results = results.count()
        self.assertEquals(3, num_results, "Expected 3 publications but "
                                          "got %s" % num_results)

    def testEmptyListOfArchives(self):
        # Passing an empty list of archives will result in an empty
        # resultset.
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, [], distribution=self.distribution)
        self.assertEquals(0, results.count())

    def testReturnsOnlyPublicationsForGivenArchives(self):
        # Returns only publications for the specified archives
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, [self.archives['gedit-beta']],
            distribution=self.distribution)
        num_results = results.count()
        self.assertEquals(1, num_results, "Expected 1 publication but "
                                          "got %s" % num_results)
        self.assertEquals(self.archives['gedit-beta'],
                          results[0].archive,
                          "Expected publication from %s but was instead "
                          "from %s." % (
                              self.archives['gedit-beta'].displayname,
                              results[0].archive.displayname
                              ))

    def testReturnsOnlyPublishedPublications(self):
        # Publications that are not published will not be returned.
        secure_src_hist = self.gedit_beta_src_hist.secure_record
        secure_src_hist.status = PackagePublishingStatus.PENDING

        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, [self.archives['gedit-beta']],
            distribution=self.distribution)
        num_results = results.count()
        self.assertEquals(0, num_results, "Expected 0 publication but "
                                          "got %s" % num_results)

    def testPubsForSpecificDistro(self):
        # Results can be filtered for specific distributions.

        # Add a publication in the ubuntu distribution
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        warty = ubuntu['warty']
        gedit_main_src_hist = self.publisher.getPubSource(
            sourcename="gedit",
            archive=self.archives['ubuntu-main'],
            distroseries=warty,
            date_uploaded=datetime(2010, 12, 30, tzinfo=pytz.UTC),
            status=PackagePublishingStatus.PUBLISHED,
            )

        # Only the 3 results for ubuntutest are returned when requested:
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values(),
            distribution=self.distribution
            )
        num_results = results.count()
        self.assertEquals(3, num_results, "Expected 3 publications but "
                                          "got %s" % num_results)

        # Similarly, requesting the ubuntu publications only returns the
        # one we created:
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values(),
            distribution=ubuntu
            )
        num_results = results.count()
        self.assertEquals(1, num_results, "Expected 1 publication but "
                                          "got %s" % num_results)


class TestArchiveRepositorySize(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestArchiveRepositorySize, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.ppa = self.factory.makeArchive(
            name="testing", distribution=self.publisher.ubuntutest)

    def test_binaries_size_does_not_include_ddebs_for_ppas(self):
        # DDEBs are not computed in the PPA binaries size because
        # they are not being published. See bug #399444.
        self.assertEquals(0, self.ppa.binaries_size)
        self.publisher.getPubBinaries(
            filecontent='X', format=BinaryPackageFormat.DDEB,
            archive=self.ppa)
        self.assertEquals(0, self.ppa.binaries_size)

    def test_binaries_size_includes_ddebs_for_other_archives(self):
        # DDEBs size are computed for all archive purposes, except PPAs.
        previous_size = self.publisher.ubuntutest.main_archive.binaries_size
        self.publisher.getPubBinaries(
            filecontent='X', format=BinaryPackageFormat.DDEB)
        self.assertEquals(
            previous_size + 1,
            self.publisher.ubuntutest.main_archive.binaries_size)


class TestSeriesWithSources(TestCaseWithFactory):
    """Create some sources in different series."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSeriesWithSources, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create three sources for the two different distroseries.
        breezy_autotest = self.publisher.distroseries
        ubuntu_test = breezy_autotest.distribution
        self.serieses = [breezy_autotest]
        self.serieses.append(self.factory.makeDistroRelease(
            distribution=ubuntu_test, name="foo-series"))

        self.sources = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.sources.append(gedit_src_hist)

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            distroseries=self.serieses[1])
        self.sources.append(firefox_src_hist)

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            status=PackagePublishingStatus.PUBLISHED,
            distroseries=self.serieses[1])
        self.sources.append(gtg_src_hist)

        # Shortcuts for test readability.
        self.archive = self.serieses[0].main_archive

    def test_series_with_sources_returns_all_series(self):
        # Calling series_with_sources returns all series with publishings.
        serieses = self.archive.series_with_sources
        serieses_names = [series.displayname for series in serieses]

        self.assertContentEqual(
            [u'Breezy Badger Autotest', u'Foo-series'],
            serieses_names)

    def test_series_with_sources_ignore_non_published_records(self):
        # If all publishings in a series are deleted or superseded
        # the series will not be returned.
        self.sources[0].secure_record.status = (
            PackagePublishingStatus.DELETED)

        serieses = self.archive.series_with_sources
        serieses_names = [series.displayname for series in serieses]

        self.assertContentEqual([u'Foo-series'], serieses_names)

    def test_series_with_sources_ordered_by_version(self):
        # The returned series are ordered by the distroseries version.
        serieses = self.archive.series_with_sources
        versions = [series.version for series in serieses]

        # Latest version should be first
        self.assertEqual(
            [u'6.6.6', u'1.0'], versions,
            "The latest version was not first.")

        # Update the version of breezyautotest and ensure that the
        # latest version is still first.
        self.serieses[0].version = u'0.5'
        serieses = self.archive.series_with_sources
        versions = [series.version for series in serieses]
        self.assertEqual(
            [u'1.0', u'0.5'], versions,
            "The latest version was not first.")

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
