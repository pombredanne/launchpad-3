# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test Build features."""

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
