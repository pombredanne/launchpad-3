# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test Build features."""

from datetime import datetime
import pytz
import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory

class TestGetPublicationsInArchive(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestGetPublicationsInArchive, self).setUp()

        ubuntu = getUtility(IDistributionSet)['ubuntutest']

        # Create two PPAs for gedit.
        self.archives = {}
        self.archives['ubuntu-main'] = ubuntu.main_archive
        self.archives['gedit-nightly'] = self.factory.makeArchive(
            name="gedit-nightly", distribution=ubuntu)
        self.archives['gedit-beta'] = self.factory.makeArchive(
            name="gedit-beta", distribution=ubuntu)

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

    def addPublicationInUbuntuDistro(self):
        """Adds a publication of gedit in the ubuntu distribution"""
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        warty = ubuntu['warty']
        gedit_main_src_hist = self.publisher.getPubSource(
            sourcename="gedit",
            archive=self.archives['ubuntu-main'],
            distroseries=warty,
            date_uploaded=datetime(2010, 12, 30, tzinfo=pytz.UTC),
            status=PackagePublishingStatus.PUBLISHED,
            )

    def testReturnsAllPublishedPublications(self):
        # Returns all currently published publications for archives
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values())
        num_results = results.count()
        self.assertEquals(3, num_results, "Expected 3 publications but "
                                          "got %s" % num_results)

    def testEmptyListOfArchives(self):
        # Passing an empty list of archives will result in an empty
        # resultset.
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, [])
        self.assertEquals(0, results.count())

    def testReturnsOnlyPublicationsForGivenArchives(self):
        # Returns only publications for the specified archives
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, [self.archives['gedit-beta']])
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
            self.gedit_name, [self.archives['gedit-beta']])
        num_results = results.count()
        self.assertEquals(0, num_results, "Expected 0 publication but "
                                          "got %s" % num_results)

    def testPubsFromAllDistros(self):
        # By default, all publications of the source package are included.

        self.addPublicationInUbuntuDistro()

        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values())
        num_results = results.count()
        self.assertEquals(4, num_results, "Expected 4 publications but "
                                          "got %s" % num_results)

    def testPubsForSpecificDistro(self):
        # Results can be filtered for specific distributions.

        self.addPublicationInUbuntuDistro()

        # We'll exclude the publication in ubuntu by requiring that
        # the distribution be ubuntutest (the distro of our test archives.)
        results = self.archive_set.getPublicationsInArchives(
            self.gedit_name, self.archives.values(),
            distribution=self.archives['ubuntu-main'].distribution
            )
        num_results = results.count()
        self.assertEquals(3, num_results, "Expected 3 publications but "
                                          "got %s" % num_results)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
