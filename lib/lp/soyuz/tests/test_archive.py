# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive features."""

from datetime import datetime, timedelta
import pytz
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import IArchiveSet, ArchivePurpose
from lp.soyuz.interfaces.binarypackagerelease import BinaryPackageFormat
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.build import Build
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

    def test_sources_size_on_empty_archive(self):
        # Zero is returned for an archive without sources.
        self.assertEquals(
            0, self.ppa.sources_size,
            'Zero should be returned for an archive without sources.')

    def test_sources_size_does_not_count_duplicated_files(self):
        # If there are multiple copies of the same file name/size
        # only one will be counted.
        pub_1 = self.publisher.getPubSource(
            filecontent='22', version='0.5.11~ppa1', archive=self.ppa)

        pub_2 = self.publisher.getPubSource(
            filecontent='333', version='0.5.11~ppa2', archive=self.ppa)

        self.assertEquals(5, self.ppa.sources_size)

        shared_tarball = self.publisher.addMockFile(
            filename='foo_0.5.11.tar.gz', filecontent='1')

        # After adding a the shared tarball to the ppa1 version,
        # the sources_size updates to reflect the change.
        pub_1.sourcepackagerelease.addFile(shared_tarball)
        self.assertEquals(
            6, self.ppa.sources_size,
            'The sources_size should update after a file is added.')

        # But after adding a copy of the shared tarball to the ppa2 version,
        # the sources_size is unchanged.
        shared_tarball_copy = self.publisher.addMockFile(
            filename='foo_0.5.11.tar.gz', filecontent='1')

        pub_2.sourcepackagerelease.addFile(shared_tarball_copy)
        self.assertEquals(
            6, self.ppa.sources_size,
            'The sources_size should change after adding a duplicate file.')


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
        self.series = [breezy_autotest]
        self.series.append(self.factory.makeDistroRelease(
            distribution=ubuntu_test, name="foo-series"))

        self.sources = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.sources.append(gedit_src_hist)

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            distroseries=self.series[1])
        self.sources.append(firefox_src_hist)

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            status=PackagePublishingStatus.PUBLISHED,
            distroseries=self.series[1])
        self.sources.append(gtg_src_hist)

        # Shortcuts for test readability.
        self.archive = self.series[0].main_archive

    def test_series_with_sources_returns_all_series(self):
        # Calling series_with_sources returns all series with publishings.
        series = self.archive.series_with_sources
        series_names = [s.displayname for s in series]

        self.assertContentEqual(
            [u'Breezy Badger Autotest', u'Foo-series'],
            series_names)

    def test_series_with_sources_ignore_non_published_records(self):
        # If all publishings in a series are deleted or superseded
        # the series will not be returned.
        self.sources[0].secure_record.status = (
            PackagePublishingStatus.DELETED)

        series = self.archive.series_with_sources
        series_names = [s.displayname for s in series]

        self.assertContentEqual([u'Foo-series'], series_names)

    def test_series_with_sources_ordered_by_version(self):
        # The returned series are ordered by the distroseries version.
        series = self.archive.series_with_sources
        versions = [s.version for s in series]

        # Latest version should be first
        self.assertEqual(
            [u'6.6.6', u'1.0'], versions,
            "The latest version was not first.")

        # Update the version of breezyautotest and ensure that the
        # latest version is still first.
        self.series[0].version = u'0.5'
        series = self.archive.series_with_sources
        versions = [s.version for s in series]
        self.assertEqual(
            [u'1.0', u'0.5'], versions,
            "The latest version was not first.")


class TestGetSourcePackageReleases(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGetSourcePackageReleases, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create an archive with some published binaries.
        self.archive = self.factory.makeArchive()
        binaries_foo = self.publisher.getPubBinaries(
            archive=self.archive, binaryname="foo-bin")
        binaries_bar = self.publisher.getPubBinaries(
            archive=self.archive, binaryname="bar-bin")

        # Collect the builds for reference.
        self.builds_foo = [
            binary.binarypackagerelease.build for binary in binaries_foo]
        self.builds_bar = [
            binary.binarypackagerelease.build for binary in binaries_bar]

        # Collect the source package releases for reference.
        self.sourcepackagereleases = [
            self.builds_foo[0].sourcepackagerelease,
            self.builds_bar[0].sourcepackagerelease,
            ]

    def test_getSourcePackageReleases_with_no_params(self):
        # With no params all source package releases are returned.
        sprs = self.archive.getSourcePackageReleases()

        self.assertContentEqual(self.sourcepackagereleases, sprs)

    def test_getSourcePackageReleases_with_buildstatus(self):
        # Results are filtered by the specified buildstatus.

        # Set the builds for one of the sprs to needs build.
        for build in self.builds_foo:
            build.buildstate = BuildStatus.NEEDSBUILD

        result = self.archive.getSourcePackageReleases(
            build_status=BuildStatus.NEEDSBUILD)

        self.failUnlessEqual(1, result.count())
        self.failUnlessEqual(
            self.sourcepackagereleases[0], result[0])

class TestCorrespondingDebugArchive(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCorrespondingDebugArchive, self).setUp()

        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']

        # Create a debug archive, as there isn't one in the sample data.
        self.debug_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.DEBUG,
            distribution=self.ubuntutest,
            owner=self.ubuntutest.owner)

        # Retrieve sample data archives of each type.
        self.primary_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PRIMARY)
        self.partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PARTNER)
        self.copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PARTNER)
        self.ppa = getUtility(IPersonSet).getByName('cprov').archive

    def testPrimaryDebugArchiveIsDebug(self):
        self.assertEquals(
            self.primary_archive.debug_archive, self.debug_archive)

    def testPartnerDebugArchiveIsSelf(self):
        self.assertEquals(
            self.partner_archive.debug_archive, self.partner_archive)

    def testCopyDebugArchiveIsSelf(self):
        self.assertEquals(
            self.copy_archive.debug_archive, self.copy_archive)

    def testDebugDebugArchiveIsSelf(self):
        self.assertEquals(
            self.debug_archive.debug_archive, self.debug_archive)

    def testPPADebugArchiveIsSelf(self):
        self.assertEquals(self.ppa.debug_archive, self.ppa)

    def testMissingPrimaryDebugArchiveIsNone(self):
        # Turn the DEBUG archive into a COPY archive to hide it.
        removeSecurityProxy(self.debug_archive).purpose = ArchivePurpose.COPY

        self.assertIs(
            self.primary_archive.debug_archive, None)


class TestArchiveEnableDisable(TestCaseWithFactory):
    """Test the enable and disable methods of Archive."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestArchiveEnableDisable, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PRIMARY)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        sample_data = store.find(Build)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        store.flush()

        # We test builds that target a primary archive.
        self.builds = []
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="apg", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="vim", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gcc", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="bison", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="flex", status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="postgres",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.archive).createMissingBuilds())
        # Set up the builds for test.
        score = 1000
        duration = 0
        for build in self.builds:
            score += 1
            duration += 60
            bq = build.buildqueue_record
            bq.lastscore = score
            bq.estimated_duration = timedelta(seconds=duration)

    def assertNoBuildJobsHaveStatus(self, archive, status):
        # Check that that the jobs attached to this archive do not have this
        # status.
        query = """
        SELECT COUNT(Job.id)
        FROM Build, BuildPackageJob, BuildQueue, Job
        WHERE
            Build.archive = %s
            AND BuildPackageJob.build = Build.id
            AND BuildPackageJob.job = BuildQueue.job
            AND Job.id = BuildQueue.job
            AND Build.buildstate = %s
            AND Job.status = %s;
        """ % sqlvalues(archive, BuildStatus.NEEDSBUILD, status)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result = store.execute(query).get_one()
        self.assertEqual(result[0], 0)

    def test_enableArchive(self):
        # Enabling an archive should set all the Archive's suspended builds to
        # WAITING.

        # Disable the archive, because it's currently enabled.
        self.archive.disable()
        self.archive.enable()
        self.assertNoBuildJobsHaveStatus(self.archive, JobStatus.SUSPENDED)
        self.assertTrue(self.archive.enabled)

    def test_enableArchiveAlreadyEnabled(self):
        # Enabling an already enabled Archive should raise an AssertionError.
        self.assertRaises(AssertionError, self.archive.enable)

    def test_disableArchive(self):
        # Disabling an archive should set all the Archive's pending bulds to
        # SUSPENDED.
        self.archive.disable()
        self.assertNoBuildJobsHaveStatus(self.archive, JobStatus.WAITING)
        self.assertFalse(self.archive.enabled)

    def test_disableArchiveAlreadyDisabled(self):
        # Disabling an already disabled Archive should raise an
        # AssertionError.
        self.archive.disable()
        self.assertRaises(AssertionError, self.archive.disable)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
