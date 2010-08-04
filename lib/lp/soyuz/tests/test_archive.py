# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive features."""

from datetime import date, timedelta

import transaction

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import (IArchiveSet, ArchivePurpose,
    ArchiveStatus, CannotRestrictArchitectures, CannotSwitchPrivacy,
    InvalidPocketForPartnerArchive, InvalidPocketForPPA)
from lp.services.worlddata.interfaces.country import ICountrySet
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageReleaseDownloadCount)
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import login, login_person, TestCaseWithFactory


class TestGetPublicationsInArchive(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeArchivesForOneDistribution(self, count=3):
        distribution = self.factory.makeDistribution()
        archives = []
        for i in range(count):
            archives.append(
                self.factory.makeArchive(distribution=distribution))
        return archives

    def makeArchivesWithPublications(self, count=3):
        archives = self.makeArchivesForOneDistribution(count=count)
        sourcepackagename = self.factory.makeSourcePackageName()
        for archive in archives:
            self.factory.makeSourcePackagePublishingHistory(
                sourcepackagename=sourcepackagename, archive=archive,
                status=PackagePublishingStatus.PUBLISHED,
                )
        return archives, sourcepackagename

    def getPublications(self, sourcepackagename, archives, distribution):
        return getUtility(IArchiveSet).getPublicationsInArchives(
            sourcepackagename, archives, distribution=distribution)

    def test_getPublications_returns_all_published_publications(self):
        # Returns all currently published publications for archives
        archives, sourcepackagename = self.makeArchivesWithPublications()
        results = self.getPublications(
            sourcepackagename, archives, archives[0].distribution)
        num_results = results.count()
        self.assertEquals(3, num_results)

    def test_getPublications_empty_list_of_archives(self):
        # Passing an empty list of archives will result in an empty
        # resultset.
        archives, sourcepackagename = self.makeArchivesWithPublications()
        results = self.getPublications(
            sourcepackagename, [], archives[0].distribution)
        self.assertEquals([], list(results))

    def assertPublicationsFromArchives(self, publications, archives):
        self.assertEquals(len(archives), publications.count())
        for publication, archive in zip(publications, archives):
            self.assertEquals(archive, publication.archive)

    def test_getPublications_returns_only_for_given_archives(self):
        # Returns only publications for the specified archives
        archives, sourcepackagename = self.makeArchivesWithPublications()
        results = self.getPublications(
            sourcepackagename, [archives[0]], archives[0].distribution)
        self.assertPublicationsFromArchives(results, [archives[0]])

    def test_getPublications_returns_only_published_publications(self):
        # Publications that are not published will not be returned.
        archive = self.factory.makeArchive()
        sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            archive=archive, sourcepackagename=sourcepackagename,
            status=PackagePublishingStatus.PENDING)
        results = self.getPublications(
            sourcepackagename, [archive], archive.distribution)
        self.assertEquals([], list(results))

    def publishSourceInNewArchive(self, sourcepackagename):
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        archive = self.factory.makeArchive(distribution=distribution)
        self.factory.makeSourcePackagePublishingHistory(
            archive=archive, sourcepackagename=sourcepackagename,
            distroseries=distroseries,
            status=PackagePublishingStatus.PUBLISHED)
        return archive

    def test_getPublications_for_specific_distro(self):
        # Results can be filtered for specific distributions.
        sourcepackagename = self.factory.makeSourcePackageName()
        archive = self.publishSourceInNewArchive(sourcepackagename)
        other_archive = self.publishSourceInNewArchive(sourcepackagename)
        # We don't get the results for other_distribution
        results = self.getPublications(
            sourcepackagename, [archive, other_archive],
            distribution=archive.distribution)
        self.assertPublicationsFromArchives(results, [archive])


class TestArchiveRepositorySize(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_empty_ppa_has_zero_binaries_size(self):
        # An empty PPA has no binaries so has zero binaries_size.
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.assertEquals(0, ppa.binaries_size)

    def test_sources_size_on_empty_archive(self):
        # Zero is returned for an archive without sources.
        archive = self.factory.makeArchive()
        self.assertEquals(0, archive.sources_size)

    def publishSourceFile(self, archive, library_file):
        """Publish a source package with the given content to the archive.

        :param archive: the IArchive to publish to.
        :param library_file: a LibraryFileAlias for the content of the
            source file.
        """
        sourcepackagerelease = self.factory.makeSourcePackageRelease()
        self.factory.makeSourcePackagePublishingHistory(
            archive=archive, sourcepackagerelease=sourcepackagerelease,
            status=PackagePublishingStatus.PUBLISHED)
        self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=sourcepackagerelease,
            library_file=library_file)

    def test_sources_size_does_not_count_duplicated_files(self):
        # If there are multiple copies of the same file name/size
        # only one will be counted.
        archive = self.factory.makeArchive()
        library_file = self.factory.makeLibraryFileAlias()
        self.publishSourceFile(archive, library_file)
        self.assertEquals(
            library_file.content.filesize, archive.sources_size)

        self.publishSourceFile(archive, library_file)
        self.assertEquals(
            library_file.content.filesize, archive.sources_size)


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
            distribution=ubuntu_test, name="foo-series", version='1.0'))

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
        self.sources[0].status = (
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
            self.builds_foo[0].source_package_release,
            self.builds_bar[0].source_package_release,
            ]

    def test_getSourcePackageReleases_with_no_params(self):
        # With no params all source package releases are returned.
        sprs = self.archive.getSourcePackageReleases()

        self.assertContentEqual(self.sourcepackagereleases, sprs)

    def test_getSourcePackageReleases_with_buildstatus(self):
        # Results are filtered by the specified buildstatus.

        # Set the builds for one of the sprs to needs build.
        for build in self.builds_foo:
            removeSecurityProxy(build).status = BuildStatus.NEEDSBUILD

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
        #XXX: rockstar - 12 Jan 2010 - Bug #506255 - Tidy up these tests!
        super(TestArchiveEnableDisable, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PRIMARY)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        sample_data = store.find(BinaryPackageBuild)
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
            removeSecurityProxy(bq).estimated_duration = timedelta(
                seconds=duration)

    def _getBuildJobsByStatus(self, archive, status):
        # Return the count for archive build jobs with the given status.
        query = """
            SELECT COUNT(Job.id)
            FROM BinaryPackageBuild, BuildPackageJob, BuildQueue, Job,
                 PackageBuild, BuildFarmJob
            WHERE
                BuildPackageJob.build = BinaryPackageBuild.id
                AND BuildPackageJob.job = BuildQueue.job
                AND Job.id = BuildQueue.job
                AND BinaryPackageBuild.package_build = PackageBuild.id
                AND PackageBuild.archive = %s
                AND PackageBuild.build_farm_job = BuildFarmJob.id
                AND BuildFarmJob.status = %s
                AND Job.status = %s;
        """ % sqlvalues(archive, BuildStatus.NEEDSBUILD, status)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.execute(query).get_one()[0]

    def assertNoBuildJobsHaveStatus(self, archive, status):
        # Check that that the jobs attached to this archive do not have this
        # status.
        self.assertEqual(self._getBuildJobsByStatus(archive, status), 0)

    def assertHasBuildJobsWithStatus(self, archive, status):
        # Check that that there are jobs attached to this archive that have
        # the specified status.
        self.assertEqual(self._getBuildJobsByStatus(archive, status), 8)

    def test_enableArchive(self):
        # Enabling an archive should set all the Archive's suspended builds to
        # WAITING.

        # Disable the archive, because it's currently enabled.
        self.archive.disable()
        self.assertHasBuildJobsWithStatus(self.archive, JobStatus.SUSPENDED)
        self.archive.enable()
        self.assertNoBuildJobsHaveStatus(self.archive, JobStatus.SUSPENDED)
        self.assertTrue(self.archive.enabled)

    def test_enableArchiveAlreadyEnabled(self):
        # Enabling an already enabled Archive should raise an AssertionError.
        self.assertRaises(AssertionError, self.archive.enable)

    def test_disableArchive(self):
        # Disabling an archive should set all the Archive's pending bulds to
        # SUSPENDED.
        self.assertHasBuildJobsWithStatus(self.archive, JobStatus.WAITING)
        self.archive.disable()
        self.assertNoBuildJobsHaveStatus(self.archive, JobStatus.WAITING)
        self.assertFalse(self.archive.enabled)

    def test_disableArchiveAlreadyDisabled(self):
        # Disabling an already disabled Archive should raise an
        # AssertionError.
        self.archive.disable()
        self.assertRaises(AssertionError, self.archive.disable)


class TestCollectLatestPublishedSources(TestCaseWithFactory):
    """Ensure that the private helper method works as expected."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup an archive with relevant publications."""
        super(TestCollectLatestPublishedSources, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create an archive with some published sources. We'll store
        # a reference to the naked archive so that we can call
        # the private method which is not defined on the interface.
        self.archive = self.factory.makeArchive()
        self.naked_archive = removeSecurityProxy(self.archive)

        self.pub_1 = self.publisher.getPubSource(
            version='0.5.11~ppa1', archive=self.archive, sourcename="foo",
            status=PackagePublishingStatus.PUBLISHED)

        self.pub_2 = self.publisher.getPubSource(
            version='0.5.11~ppa2', archive=self.archive, sourcename="foo",
            status=PackagePublishingStatus.PUBLISHED)

        self.pub_3 = self.publisher.getPubSource(
            version='0.9', archive=self.archive, sourcename="bar",
            status=PackagePublishingStatus.PUBLISHED)

    def test_collectLatestPublishedSources_returns_latest(self):
        pubs = self.naked_archive._collectLatestPublishedSources(
            self.archive, ["foo"])
        self.assertEqual(1, len(pubs))
        self.assertEqual('0.5.11~ppa2', pubs[0].source_package_version)

    def test_collectLatestPublishedSources_returns_published_only(self):
        # Set the status of the latest pub to DELETED and ensure that it
        # is not returned.
        self.pub_2.status = PackagePublishingStatus.DELETED

        pubs = self.naked_archive._collectLatestPublishedSources(
            self.archive, ["foo"])
        self.assertEqual(1, len(pubs))
        self.assertEqual('0.5.11~ppa1', pubs[0].source_package_version)


class TestArchiveCanUpload(TestCaseWithFactory):
    """Test the various methods that verify whether uploads are allowed to
    happen."""

    layer = LaunchpadZopelessLayer

    def test_checkArchivePermission_by_PPA_owner(self):
        # Uploading to a PPA should be allowed for a user that is the owner
        owner = self.factory.makePerson(name="somebody")
        archive = self.factory.makeArchive(owner=owner)
        self.assertEquals(True, archive.checkArchivePermission(owner))
        someone_unrelated = self.factory.makePerson(name="somebody-unrelated")
        self.assertEquals(False,
            archive.checkArchivePermission(someone_unrelated))

    def test_checkArchivePermission_distro_archive(self):
        # Regular users can not upload to ubuntu
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY,
                                           distribution=ubuntu)
        main = getUtility(IComponentSet)["main"]
        # A regular user doesn't have access
        somebody = self.factory.makePerson(name="somebody")
        self.assertEquals(False,
            archive.checkArchivePermission(somebody, main))
        # An ubuntu core developer does have access
        kamion = getUtility(IPersonSet).getByName('kamion')
        self.assertEquals(True, archive.checkArchivePermission(kamion, main))

    def test_checkArchivePermission_ppa(self):
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        owner = self.factory.makePerson(name="eigenaar")
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA,
                                           distribution=ubuntu,
                                           owner=owner)
        somebody = self.factory.makePerson(name="somebody")
        # The owner has access
        self.assertEquals(True, archive.checkArchivePermission(owner))
        # Somebody unrelated does not
        self.assertEquals(False, archive.checkArchivePermission(somebody))

    def test_checkUpload_partner_invalid_pocket(self):
        # Partner archives only have release and proposed pockets
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PARTNER)
        self.assertIsInstance(archive.checkUpload(self.factory.makePerson(),
                                self.factory.makeDistroSeries(),
                                self.factory.makeSourcePackageName(),
                                self.factory.makeComponent(),
                                PackagePublishingPocket.UPDATES),
                                InvalidPocketForPartnerArchive)

    def test_checkUpload_ppa_invalid_pocket(self):
        # PPA archives only have release pockets
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.assertIsInstance(archive.checkUpload(self.factory.makePerson(),
                                self.factory.makeDistroSeries(),
                                self.factory.makeSourcePackageName(),
                                self.factory.makeComponent(),
                                PackagePublishingPocket.PROPOSED),
                                InvalidPocketForPPA)
    # XXX: JRV 20100511: IArchive.canUploadSuiteSourcePackage needs tests


class TestUpdatePackageDownloadCount(TestCaseWithFactory):
    """Ensure that updatePackageDownloadCount works as expected."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestUpdatePackageDownloadCount, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

        self.archive = self.factory.makeArchive()
        self.bpr_1 = self.publisher.getPubBinaries(
                archive=self.archive)[0].binarypackagerelease
        self.bpr_2 = self.publisher.getPubBinaries(
                archive=self.archive)[0].binarypackagerelease

        country_set = getUtility(ICountrySet)
        self.australia = country_set['AU']
        self.new_zealand = country_set['NZ']

    def assertCount(self, count, archive, bpr, day, country):
        self.assertEqual(count, self.store.find(
            BinaryPackageReleaseDownloadCount,
            archive=archive, binary_package_release=bpr,
            day=day, country=country).one().count)

    def test_creates_new_entry(self):
        # The first update for a particular archive, package, day and
        # country will create a new BinaryPackageReleaseDownloadCount
        # entry.
        day = date(2010, 2, 20)
        self.assertIs(None, self.store.find(
            BinaryPackageReleaseDownloadCount,
            archive=self.archive, binary_package_release=self.bpr_1,
            day=day, country=self.australia).one())
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.assertCount(10, self.archive, self.bpr_1, day, self.australia)

    def test_reuses_existing_entry(self):
        # A second update will simply add to the count on the existing
        # BPRDC.
        day = date(2010, 2, 20)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 3)
        self.assertCount(13, self.archive, self.bpr_1, day, self.australia)

    def test_differentiates_between_countries(self):
        # A different country will cause a new entry to be created.
        day = date(2010, 2, 20)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.new_zealand, 3)

        self.assertCount(10, self.archive, self.bpr_1, day, self.australia)
        self.assertCount(3, self.archive, self.bpr_1, day, self.new_zealand)

    def test_country_can_be_none(self):
        # The country can be None, indicating that it is unknown.
        day = date(2010, 2, 20)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, None, 3)

        self.assertCount(10, self.archive, self.bpr_1, day, self.australia)
        self.assertCount(3, self.archive, self.bpr_1, day, None)

    def test_differentiates_between_days(self):
        # A different date will also cause a new entry to be created.
        day = date(2010, 2, 20)
        another_day = date(2010, 2, 21)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, another_day, self.australia, 3)

        self.assertCount(10, self.archive, self.bpr_1, day, self.australia)
        self.assertCount(
            3, self.archive, self.bpr_1, another_day, self.australia)

    def test_differentiates_between_bprs(self):
        # And even a different package will create a new entry.
        day = date(2010, 2, 20)
        self.archive.updatePackageDownloadCount(
            self.bpr_1, day, self.australia, 10)
        self.archive.updatePackageDownloadCount(
            self.bpr_2, day, self.australia, 3)

        self.assertCount(10, self.archive, self.bpr_1, day, self.australia)
        self.assertCount(3, self.archive, self.bpr_2, day, self.australia)


class TestEnabledRestrictedBuilds(TestCaseWithFactory):
    """Ensure that restricted architecture family builds can be allowed and
    disallowed correctly."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup an archive with relevant publications."""
        super(TestEnabledRestrictedBuilds, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.archive = self.factory.makeArchive()
        self.archive_arch_set = getUtility(IArchiveArchSet)
        self.arm = getUtility(IProcessorFamilySet).getByName('arm')

    def test_main_archive_can_use_restricted(self):
        # Main archives for distributions can always use restricted
        # architectures.
        distro = self.factory.makeDistribution()
        self.assertContentEqual([self.arm],
            distro.main_archive.enabled_restricted_families)

    def test_main_archive_can_not_be_restricted(self):
        # A main archive can not be restricted to certain architectures.
        distro = self.factory.makeDistribution()
        # Restricting to all restricted architectures is fine
        distro.main_archive.enabled_restricted_families = [self.arm]

        def restrict():
            distro.main_archive.enabled_restricted_families = []

        self.assertRaises(CannotRestrictArchitectures, restrict)

    def test_default(self):
        """By default, ARM builds are not allowed as ARM is restricted."""
        self.assertEquals(0,
            self.archive_arch_set.getByArchive(
                self.archive, self.arm).count())
        self.assertContentEqual([], self.archive.enabled_restricted_families)

    def test_get_uses_archivearch(self):
        """Adding an entry to ArchiveArch for ARM and an archive will
        enable enabled_restricted_families for arm for that archive."""
        self.assertContentEqual([], self.archive.enabled_restricted_families)
        self.archive_arch_set.new(self.archive, self.arm)
        self.assertEquals([self.arm],
                list(self.archive.enabled_restricted_families))

    def test_get_returns_restricted_only(self):
        """Adding an entry to ArchiveArch for something that is not
        restricted does not make it show up in enabled_restricted_families.
        """
        self.assertContentEqual([], self.archive.enabled_restricted_families)
        self.archive_arch_set.new(self.archive,
            getUtility(IProcessorFamilySet).getByName('amd64'))
        self.assertContentEqual([], self.archive.enabled_restricted_families)

    def test_set(self):
        """The property remembers its value correctly and sets ArchiveArch."""
        self.archive.enabled_restricted_families = [self.arm]
        allowed_restricted_families = self.archive_arch_set.getByArchive(
            self.archive, self.arm)
        self.assertEquals(1, allowed_restricted_families.count())
        self.assertEquals(self.arm,
            allowed_restricted_families[0].processorfamily)
        self.assertEquals(
            [self.arm], self.archive.enabled_restricted_families)
        self.archive.enabled_restricted_families = []
        self.assertEquals(0,
            self.archive_arch_set.getByArchive(
                self.archive, self.arm).count())
        self.assertContentEqual([], self.archive.enabled_restricted_families)


class TestArchiveTokens(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestArchiveTokens, self).setUp()
        owner = self.factory.makePerson()
        self.private_ppa = self.factory.makeArchive(owner=owner)
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True
        self.joe = self.factory.makePerson(name='joe')
        self.private_ppa.newSubscription(self.joe, owner)

    def test_getAuthToken_with_no_token(self):
        token = self.private_ppa.getAuthToken(self.joe)
        self.assertEqual(token, None)

    def test_getAuthToken_with_token(self):
        token = self.private_ppa.newAuthToken(self.joe)
        self.assertEqual(self.private_ppa.getAuthToken(self.joe), token)

    def test_getArchiveSubscriptionURL(self):
        url = self.joe.getArchiveSubscriptionURL(self.joe, self.private_ppa)
        token = self.private_ppa.getAuthToken(self.joe)
        self.assertEqual(token.archive_url, url)


class TestArchivePrivacySwitching(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create a public and a private PPA."""
        super(TestArchivePrivacySwitching, self).setUp()
        self.public_ppa = self.factory.makeArchive()
        self.private_ppa = self.factory.makeArchive()
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True

    def make_ppa_private(self, ppa):
        """Helper method to privatise a ppa."""
        ppa.private = True
        ppa.buildd_secret = "secret"

    def make_ppa_public(self, ppa):
        """Helper method to make a PPA public (and use for assertRaises)."""
        ppa.private = False
        ppa.buildd_secret = ''

    def test_switch_privacy_no_pubs_succeeds(self):
        # Changing the privacy is fine if there are no publishing
        # records.
        self.make_ppa_private(self.public_ppa)
        self.assertTrue(self.public_ppa.private)

        self.private_ppa.private = False
        self.assertFalse(self.private_ppa.private)

    def test_switch_privacy_with_pubs_fails(self):
        # Changing the privacy is not possible when the archive already
        # has published sources.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        publisher.getPubSource(archive=self.public_ppa)
        publisher.getPubSource(archive=self.private_ppa)

        self.assertRaises(
            CannotSwitchPrivacy, self.make_ppa_private, self.public_ppa)

        self.assertRaises(
            CannotSwitchPrivacy, self.make_ppa_public, self.private_ppa)


class TestGetBinaryPackageRelease(TestCaseWithFactory):
    """Ensure that getBinaryPackageRelease works as expected."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup an archive with relevant publications."""
        super(TestGetBinaryPackageRelease, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.archive = self.factory.makeArchive()
        self.archive.require_virtualized = False

        self.i386_pub, self.hppa_pub = self.publisher.getPubBinaries(
            version="1.2.3-4", archive=self.archive, binaryname="foo-bin",
            status=PackagePublishingStatus.PUBLISHED,
            architecturespecific=True)

        self.i386_indep_pub, self.hppa_indep_pub = (
            self.publisher.getPubBinaries(
                version="1.2.3-4", archive=self.archive, binaryname="bar-bin",
                status=PackagePublishingStatus.PUBLISHED))

        self.bpns = getUtility(IBinaryPackageNameSet)

    def test_returns_matching_binarypackagerelease(self):
        # The BPR with a file by the given name should be returned.
        self.assertEqual(
            self.i386_pub.binarypackagerelease,
            self.archive.getBinaryPackageRelease(
                self.bpns['foo-bin'], '1.2.3-4', 'i386'))

    def test_returns_correct_architecture(self):
        # The architecture is taken into account correctly.
        self.assertEqual(
            self.hppa_pub.binarypackagerelease,
            self.archive.getBinaryPackageRelease(
                self.bpns['foo-bin'], '1.2.3-4', 'hppa'))

    def test_works_with_architecture_independent_binaries(self):
        # Architecture independent binaries with multiple publishings
        # are found properly.
        # We use 'i386' as the arch tag here, since what we have in the DB
        # is the *build* arch tag, not the one in the filename ('all').
        self.assertEqual(
            self.i386_indep_pub.binarypackagerelease,
            self.archive.getBinaryPackageRelease(
                self.bpns['bar-bin'], '1.2.3-4', 'i386'))

    def test_returns_none_for_nonexistent_binary(self):
        # Non-existent files return None.
        self.assertIs(
            None,
            self.archive.getBinaryPackageRelease(
                self.bpns['cdrkit'], '1.2.3-4', 'i386'))

    def test_returns_none_for_duplicate_file(self):
        # In the unlikely case of multiple BPRs in this archive with the same
        # name (hopefully impossible, but it still happens occasionally due
        # to bugs), None is returned.

        # Publish the same binaries again. Evil.
        self.publisher.getPubBinaries(
            version="1.2.3-4", archive=self.archive, binaryname="foo-bin",
            status=PackagePublishingStatus.PUBLISHED,
            architecturespecific=True)

        self.assertIs(
            None,
            self.archive.getBinaryPackageRelease(
                self.bpns['foo-bin'], '1.2.3-4', 'i386'))

    def test_returns_none_from_another_archive(self):
        # Cross-archive searches are not performed.
        self.assertIs(
            None,
            self.factory.makeArchive().getBinaryPackageRelease(
                self.bpns['foo-bin'], '1.2.3-4', 'i386'))


class TestGetBinaryPackageReleaseByFileName(TestCaseWithFactory):
    """Ensure that getBinaryPackageReleaseByFileName works as expected."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup an archive with relevant publications."""
        super(TestGetBinaryPackageReleaseByFileName, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.archive = self.factory.makeArchive()
        self.archive.require_virtualized = False

        self.i386_pub, self.hppa_pub = self.publisher.getPubBinaries(
            version="1.2.3-4", archive=self.archive, binaryname="foo-bin",
            status=PackagePublishingStatus.PUBLISHED,
            architecturespecific=True)

        self.i386_indep_pub, self.hppa_indep_pub = (
            self.publisher.getPubBinaries(
                version="1.2.3-4", archive=self.archive, binaryname="bar-bin",
                status=PackagePublishingStatus.PUBLISHED))

    def test_returns_matching_binarypackagerelease(self):
        # The BPR with a file by the given name should be returned.
        self.assertEqual(
            self.i386_pub.binarypackagerelease,
            self.archive.getBinaryPackageReleaseByFileName(
                "foo-bin_1.2.3-4_i386.deb"))

    def test_returns_correct_architecture(self):
        # The architecture is taken into account correctly.
        self.assertEqual(
            self.hppa_pub.binarypackagerelease,
            self.archive.getBinaryPackageReleaseByFileName(
                "foo-bin_1.2.3-4_hppa.deb"))

    def test_works_with_architecture_independent_binaries(self):
        # Architecture independent binaries with multiple publishings
        # are found properly.
        self.assertEqual(
            self.i386_indep_pub.binarypackagerelease,
            self.archive.getBinaryPackageReleaseByFileName(
                "bar-bin_1.2.3-4_all.deb"))

    def test_returns_none_for_source_file(self):
        # None is returned if the file is a source component instead.
        self.assertIs(
            None,
            self.archive.getBinaryPackageReleaseByFileName(
                "foo_1.2.3-4.dsc"))

    def test_returns_none_for_nonexistent_file(self):
        # Non-existent files return None.
        self.assertIs(
            None,
            self.archive.getBinaryPackageReleaseByFileName(
                "this-is-not-real_1.2.3-4_all.deb"))

    def test_returns_none_for_duplicate_file(self):
        # In the unlikely case of multiple BPRs in this archive with the same
        # name (hopefully impossible, but it still happens occasionally due
        # to bugs), None is returned.

        # Publish the same binaries again. Evil.
        self.publisher.getPubBinaries(
            version="1.2.3-4", archive=self.archive, binaryname="foo-bin",
            status=PackagePublishingStatus.PUBLISHED,
            architecturespecific=True)

        self.assertIs(
            None,
            self.archive.getBinaryPackageReleaseByFileName(
                "foo-bin_1.2.3-4_i386.deb"))

    def test_returns_none_from_another_archive(self):
        # Cross-archive searches are not performed.
        self.assertIs(
            None,
            self.factory.makeArchive().getBinaryPackageReleaseByFileName(
                "foo-bin_1.2.3-4_i386.deb"))


class TestArchiveDelete(TestCaseWithFactory):
    """Edge-case tests for PPA deletion.

    PPA deletion is also documented in lp/soyuz/doc/archive-deletion.txt.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a test archive and login as the owner."""
        super(TestArchiveDelete, self).setUp()
        self.archive = self.factory.makeArchive()
        login_person(self.archive.owner)

    def test_delete(self):
        # Sanity check for the unit-test.
        self.archive.delete(deleted_by=self.archive.owner)
        self.failUnlessEqual(ArchiveStatus.DELETING, self.archive.status)

    def test_delete_when_disabled(self):
        # A disabled archive can also be deleted (bug 574246).
        self.archive.disable()
        self.archive.delete(deleted_by=self.archive.owner)
        self.failUnlessEqual(ArchiveStatus.DELETING, self.archive.status)


class TestCommercialArchive(TestCaseWithFactory):
    """Tests relating to commercial archives."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestCommercialArchive, self).setUp()
        self.archive = self.factory.makeArchive()

    def setCommercial(self, archive, commercial):
        """Helper function."""
        archive.commercial = commercial

    def test_set_and_get_commercial(self):
        # Basic set and get of the commercial property.  Anyone can read
        # it and it defaults to False.
        login_person(self.archive.owner)
        self.assertFalse(self.archive.commercial)

        # The archive owner can't change the value.
        self.assertRaises(
            Unauthorized, self.setCommercial, self.archive, True)

        # Commercial admins can change it.
        login("commercial-member@canonical.com")
        self.setCommercial(self.archive, True)
        self.assertTrue(self.archive.commercial)


class TestFindDepCandidates(TestCaseWithFactory):
    """Tests for Archive.findDepCandidates."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindDepCandidates, self).setUp()
        self.archive = self.factory.makeArchive()
        self.publisher = SoyuzTestPublisher()
        login('admin@canonical.com')
        self.publisher.prepareBreezyAutotest()

    def assertDep(self, arch_tag, name, expected, archive=None,
                  pocket=PackagePublishingPocket.RELEASE, component=None,
                  source_package_name='something-new'):
        """Helper to check that findDepCandidates works.

        Searches for the given dependency name in the given architecture and
        archive, and compares it to the given expected value.
        The archive defaults to self.archive.

        Also commits, since findDepCandidates uses the slave store.
        """
        transaction.commit()

        if component is None:
            component = getUtility(IComponentSet)['main']
        if archive is None:
            archive = self.archive

        self.assertEquals(
            list(
                archive.findDepCandidates(
                    self.publisher.distroseries[arch_tag], pocket, component,
                    source_package_name, name)),
            expected)

    def test_finds_candidate_in_same_archive(self):
        # A published candidate in the same archive should be found.
        bins = self.publisher.getPubBinaries(
            binaryname='foo', archive=self.archive,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertDep('i386', 'foo', [bins[0]])
        self.assertDep('hppa', 'foo', [bins[1]])

    def test_does_not_find_pending_publication(self):
        # A pending candidate in the same archive should not be found.
        bins = self.publisher.getPubBinaries(
            binaryname='foo', archive=self.archive)
        self.assertDep('i386', 'foo', [])

    def test_ppa_searches_primary_archive(self):
        # PPA searches implicitly look in the primary archive too.
        self.assertEquals(self.archive.purpose, ArchivePurpose.PPA)
        self.assertDep('i386', 'foo', [])

        bins = self.publisher.getPubBinaries(
            binaryname='foo', archive=self.archive.distribution.main_archive,
            status=PackagePublishingStatus.PUBLISHED)

        self.assertDep('i386', 'foo', [bins[0]])

    def test_searches_dependencies(self):
        # Candidates from archives on which the target explicitly depends
        # should be found.
        bins = self.publisher.getPubBinaries(
            binaryname='foo', archive=self.archive,
            status=PackagePublishingStatus.PUBLISHED)
        other_archive = self.factory.makeArchive()
        self.assertDep('i386', 'foo', [], archive=other_archive)

        other_archive.addArchiveDependency(
            self.archive, PackagePublishingPocket.RELEASE)
        self.assertDep('i386', 'foo', [bins[0]], archive=other_archive)

    def test_obeys_dependency_pockets(self):
        # Only packages published in a pocket matching the dependency should
        # be found.
        release_bins = self.publisher.getPubBinaries(
            binaryname='foo-release', archive=self.archive,
            status=PackagePublishingStatus.PUBLISHED)
        updates_bins = self.publisher.getPubBinaries(
            binaryname='foo-updates', archive=self.archive,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.UPDATES)
        proposed_bins = self.publisher.getPubBinaries(
            binaryname='foo-proposed', archive=self.archive,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.PROPOSED)

        # Temporarily turn our test PPA into a copy archive, so we can
        # add non-RELEASE dependencies on it.
        removeSecurityProxy(self.archive).purpose = ArchivePurpose.COPY

        other_archive = self.factory.makeArchive()
        other_archive.addArchiveDependency(
            self.archive, PackagePublishingPocket.UPDATES)
        self.assertDep(
            'i386', 'foo-release', [release_bins[0]], archive=other_archive)
        self.assertDep(
            'i386', 'foo-updates', [updates_bins[0]], archive=other_archive)
        self.assertDep('i386', 'foo-proposed', [], archive=other_archive)

        other_archive.removeArchiveDependency(self.archive)
        other_archive.addArchiveDependency(
            self.archive, PackagePublishingPocket.PROPOSED)
        self.assertDep(
            'i386', 'foo-proposed', [proposed_bins[0]], archive=other_archive)

    def test_obeys_dependency_components(self):
        # Only packages published in a component matching the dependency
        # should be found.
        primary = self.archive.distribution.main_archive
        main_bins = self.publisher.getPubBinaries(
            binaryname='foo-main', archive=primary, component='main',
            status=PackagePublishingStatus.PUBLISHED)
        universe_bins = self.publisher.getPubBinaries(
            binaryname='foo-universe', archive=primary,
            component='universe',
            status=PackagePublishingStatus.PUBLISHED)

        self.archive.addArchiveDependency(
            primary, PackagePublishingPocket.RELEASE,
            component=getUtility(IComponentSet)['main'])
        self.assertDep('i386', 'foo-main', [main_bins[0]])
        self.assertDep('i386', 'foo-universe', [])

        self.archive.removeArchiveDependency(primary)
        self.archive.addArchiveDependency(
            primary, PackagePublishingPocket.RELEASE,
            component=getUtility(IComponentSet)['universe'])
        self.assertDep('i386', 'foo-main', [main_bins[0]])
        self.assertDep('i386', 'foo-universe', [universe_bins[0]])
