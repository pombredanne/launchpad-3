# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from simplejson import dumps
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
from lp.services.log.logger import DevNullLogger
from lp.services.webapp.interaction import ANONYMOUS
from lp.services.webapp.interfaces import OAuthPermission
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import (
    IBinaryPackageBuild,
    IBinaryPackageBuildSet,
    UnparsableDependencies,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.binarypackagebuild import (
    BinaryPackageBuildSet,
    COPY_ARCHIVE_SCORE_PENALTY,
    PRIVATE_ARCHIVE_SCORE_BONUS,
    SCORE_BY_COMPONENT,
    SCORE_BY_POCKET,
    SCORE_BY_URGENCY,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    anonymous_logged_in,
    api_url,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.pages import webservice_for_person


class TestBinaryPackageBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBinaryPackageBuild, self).setUp()
        self.build = self.factory.makeBinaryPackageBuild(
            archive=self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY))

    def test_providesInterfaces(self):
        # Build provides IPackageBuild and IBuild.
        self.assertProvides(self.build, IPackageBuild)
        self.assertProvides(self.build, IBinaryPackageBuild)

    def test_queueBuild(self):
        # BinaryPackageBuild can create the queue entry for itself.
        bq = self.build.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertEqual(
            self.build.build_farm_job, removeSecurityProxy(bq)._build_farm_job)
        self.assertEqual(self.build, bq.specific_build)
        self.assertEqual(self.build.virtualized, bq.virtualized)
        self.assertIsNotNone(bq.processor)
        self.assertEqual(bq, self.build.buildqueue_record)

    def test_estimateDuration(self):
        # Without previous builds, a negligable package size estimate is
        # 300s.
        self.assertEqual(300, self.build.estimateDuration().seconds)

    def create_previous_build(self, duration):
        spr = self.build.source_package_release
        build = getUtility(IBinaryPackageBuildSet).new(
            spr, self.build.archive, self.build.distro_arch_series,
            self.build.pocket)
        now = datetime.now(pytz.UTC)
        build.updateStatus(
            BuildStatus.BUILDING,
            date_started=now - timedelta(seconds=duration))
        build.updateStatus(BuildStatus.FULLYBUILT, date_finished=now)
        return build

    def test_estimateDuration_with_history(self):
        # Previous builds of the same source are used for estimates.
        self.create_previous_build(335)
        self.assertEqual(335, self.build.estimateDuration().seconds)

    def test_build_cookie(self):
        build = self.factory.makeBinaryPackageBuild()
        self.assertEqual('PACKAGEBUILD-%d' % build.id, build.build_cookie)

    def addFakeBuildLog(self, build):
        build.setLog(self.factory.makeLibraryFileAlias('mybuildlog.txt'))

    def test_log_url(self):
        # The log URL for a binary package build will use
        # the distribution source package release when the context
        # is not a PPA or a copy archive.
        self.addFakeBuildLog(self.build)
        self.assertEqual(
            'http://launchpad.dev/%s/+source/'
            '%s/%s/+build/%d/+files/mybuildlog.txt' % (
                self.build.distribution.name,
                self.build.source_package_release.sourcepackagename.name,
                self.build.source_package_release.version, self.build.id),
            self.build.log_url)

    def test_log_url_ppa(self):
        # On the other hand, ppa or copy builds will have a url in the
        # context of the archive.
        build = self.factory.makeBinaryPackageBuild(
            archive=self.factory.makeArchive(purpose=ArchivePurpose.PPA))
        self.addFakeBuildLog(build)
        self.assertEqual(
            'http://launchpad.dev/~%s/+archive/%s/'
            '%s/+build/%d/+files/mybuildlog.txt' % (
                build.archive.owner.name, build.archive.distribution.name,
                build.archive.name, build.id),
            build.log_url)

    def test_getUploader(self):
        # For ACL purposes the uploader is the changes file signer.

        class MockChanges:
            signer = "Somebody <somebody@ubuntu.com>"

        self.assertEqual("Somebody <somebody@ubuntu.com>",
            self.build.getUploader(MockChanges()))

    def test_can_be_cancelled(self):
        # For all states that can be cancelled, assert can_be_cancelled
        # returns True.
        ok_cases = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        for status in BuildStatus:
            if status in ok_cases:
                self.assertTrue(self.build.can_be_cancelled)
            else:
                self.assertFalse(self.build.can_be_cancelled)

    def test_can_be_cancelled_virtuality(self):
        # Both virtual and non-virtual builds can be cancelled.
        bq = removeSecurityProxy(self.build.queueBuild())
        bq.virtualized = True
        self.assertTrue(self.build.can_be_cancelled)
        bq.virtualized = False
        self.assertTrue(self.build.can_be_cancelled)

    def test_cancel_not_in_progress(self):
        # Testing the cancel() method for a pending build should leave
        # it in the CANCELLED state.
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        build = self.factory.makeBinaryPackageBuild(archive=ppa)
        build.queueBuild()
        build.cancel()
        self.assertEqual(BuildStatus.CANCELLED, build.status)
        self.assertIs(None, build.buildqueue_record)

    def test_cancel_in_progress(self):
        # Testing the cancel() method for a building build should leave
        # it in the CANCELLING state.
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        build = self.factory.makeBinaryPackageBuild(archive=ppa)
        bq = build.queueBuild()
        bq.markAsBuilding(self.factory.makeBuilder())
        build.cancel()
        self.assertEqual(BuildStatus.CANCELLING, build.status)
        self.assertEqual(bq, build.buildqueue_record)

    def test_getLatestSourcePublication(self):
        distroseries = self.factory.makeDistroSeries()
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution)
        other_archive = self.factory.makeArchive(
            distribution=distroseries.distribution)
        spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, archive=archive)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, archive=other_archive,
            sourcepackagerelease=spph.sourcepackagerelease)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        build = self.factory.makeBinaryPackageBuild(
            source_package_release=spph.sourcepackagerelease,
            distroarchseries=das, archive=archive)
        self.assertEqual(spph, build.getLatestSourcePublication())


class TestBuildUpdateDependencies(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def _setupSimpleDepwaitContext(self):
        """Use `SoyuzTestPublisher` to setup a simple depwait context.

        Return an `IBinaryPackageBuild` in MANUALDEWAIT state and depending
        on a binary that exists and is reachable.
        """
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        depwait_source = self.publisher.getPubSource(
            sourcename='depwait-source')

        self.publisher.getPubBinaries(
            binaryname='dep-bin',
            status=PackagePublishingStatus.PUBLISHED)

        [depwait_build] = depwait_source.createMissingBuilds()
        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin'})
        return depwait_build

    def testUpdateDependenciesWorks(self):
        # Calling `IBinaryPackageBuild.updateDependencies` makes the build
        # record ready for dispatch.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, '')

    def assertRaisesUnparsableDependencies(self, depwait_build, dependencies):
        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': dependencies})
        self.assertRaises(
            UnparsableDependencies, depwait_build.updateDependencies)

    def testInvalidDependencies(self):
        # Calling `IBinaryPackageBuild.updateDependencies` on a build with
        # invalid 'dependencies' raises an AssertionError.
        # Anything not following '<name> [([relation] <version>)][, ...]'
        depwait_build = self._setupSimpleDepwaitContext()

        # None is not a valid dependency values.
        self.assertRaisesUnparsableDependencies(depwait_build, None)

        # Missing 'name'.
        self.assertRaisesUnparsableDependencies(depwait_build, u'(>> version)')

        # Missing 'version'.
        self.assertRaisesUnparsableDependencies(depwait_build, u'name (>>)')

        # Missing comma between dependencies.
        self.assertRaisesUnparsableDependencies(depwait_build, u'name1 name2')

    def testBug378828(self):
        # `IBinaryPackageBuild.updateDependencies` copes with the
        # scenario where the corresponding source publication is not
        # active (deleted) and the source original component is not a
        # valid ubuntu component.
        depwait_build = self._setupSimpleDepwaitContext()

        spr = depwait_build.source_package_release
        depwait_build.current_source_publication.requestDeletion(
            spr.creator)
        contrib = getUtility(IComponentSet).new('contrib')
        removeSecurityProxy(spr).component = contrib

        self.layer.txn.commit()
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, '')

    def testVersionedDependencies(self):
        # `IBinaryPackageBuild.updateDependencies` supports versioned
        # dependencies. A build will not be retried unless the candidate
        # complies with the version restriction.
        # In this case, dep-bin 666 is available. >> 666 isn't
        # satisified, but >= 666 is.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()

        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (>> 666)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'dep-bin (>> 666)')
        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (>= 666)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'')

    def testVersionedDependencyOnOldPublication(self):
        # `IBinaryPackageBuild.updateDependencies` doesn't just consider
        # the latest publication. There may be older publications which
        # satisfy the version constraints (in other archives or pockets).
        # In this case, dep-bin 666 and 999 are available, so both = 666
        # and = 999 are satisfied.
        depwait_build = self._setupSimpleDepwaitContext()
        self.publisher.getPubBinaries(
            binaryname='dep-bin', version='999',
            status=PackagePublishingStatus.PUBLISHED)
        self.layer.txn.commit()

        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (= 666)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'')
        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (= 999)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'')

    def testStrictInequalities(self):
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()

        for dep, expected in (
                (u'dep-bin (<< 444)', u'dep-bin (<< 444)'),
                (u'dep-bin (>> 444)', u''),
                (u'dep-bin (<< 888)', u''),
                (u'dep-bin (>> 888)', u'dep-bin (>> 888)'),
                ):
            depwait_build.updateStatus(
                BuildStatus.MANUALDEPWAIT, slave_status={'dependencies': dep})
            depwait_build.updateDependencies()
            self.assertEqual(expected, depwait_build.dependencies)

    def testDisjunctions(self):
        # If one of a set of alternatives becomes available, that set of
        # alternatives is dropped from the outstanding dependencies.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()

        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={
                'dependencies': u'dep-bin (>= 999) | alt-bin, dep-tools'})
        depwait_build.updateDependencies()
        self.assertEqual(
            u'dep-bin (>= 999) | alt-bin, dep-tools',
            depwait_build.dependencies)

        self.publisher.getPubBinaries(
            binaryname='alt-bin', status=PackagePublishingStatus.PUBLISHED)
        self.layer.txn.commit()

        depwait_build.updateDependencies()
        self.assertEqual(u'dep-tools', depwait_build.dependencies)

    def testAptVersionConstraints(self):
        # launchpad-buildd can return apt-style version constraints
        # using < and > rather than << and >>.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()

        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (> 666), dep-bin (< 777)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'dep-bin (> 666)')
        depwait_build.updateStatus(
            BuildStatus.MANUALDEPWAIT,
            slave_status={'dependencies': u'dep-bin (> 665)'})
        depwait_build.updateDependencies()
        self.assertEqual(depwait_build.dependencies, u'')


class BaseTestCaseWithThreeBuilds(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some builds for the test archive."""
        super(BaseTestCaseWithThreeBuilds, self).setUp()
        self.ds = self.factory.makeDistroSeries()
        i386_das = self.factory.makeDistroArchSeries(
            distroseries=self.ds, architecturetag='i386')
        hppa_das = self.factory.makeDistroArchSeries(
            distroseries=self.ds, architecturetag='hppa')
        self.builds = [
            self.factory.makeBinaryPackageBuild(
                archive=self.ds.main_archive, distroarchseries=i386_das),
            self.factory.makeBinaryPackageBuild(
                archive=self.ds.main_archive, distroarchseries=i386_das,
                pocket=PackagePublishingPocket.PROPOSED),
            self.factory.makeBinaryPackageBuild(
                archive=self.ds.main_archive, distroarchseries=hppa_das),
            ]
        self.sources = [
            build.current_source_publication for build in self.builds]


class TestBuildSet(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_getByBuildFarmJob_works(self):
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertEqual(
            bpb,
            getUtility(IBinaryPackageBuildSet).getByBuildFarmJob(
                bpb.build_farm_job))

    def test_getByBuildFarmJob_returns_none_when_missing(self):
        sprb = self.factory.makeSourcePackageRecipeBuild()
        self.assertIsNone(
            getUtility(IBinaryPackageBuildSet).getByBuildFarmJob(
                sprb.build_farm_job))

    def test_getByBuildFarmJobs_works(self):
        bpbs = [self.factory.makeBinaryPackageBuild() for i in xrange(10)]
        self.assertContentEqual(
            bpbs,
            getUtility(IBinaryPackageBuildSet).getByBuildFarmJobs(
                [bpb.build_farm_job for bpb in bpbs]))

    def test_getByBuildFarmJobs_works_empty(self):
        self.assertContentEqual(
            [],
            getUtility(IBinaryPackageBuildSet).getByBuildFarmJobs([]))


class TestBuildSetGetBuildsForArchive(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestBuildSetGetBuildsForArchive, self).setUp()

        # Short-cuts for our tests.
        self.archive = self.ds.main_archive
        self.build_set = getUtility(IBinaryPackageBuildSet)

    def test_getBuildsForArchive_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForArchive(self.archive)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForArchive_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:2]
        builds = self.build_set.getBuildsForArchive(self.archive,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)


class TestBuildSetGetBuildsForBuilder(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        super(TestBuildSetGetBuildsForBuilder, self).setUp()

        # Short-cuts for our tests.
        self.build_set = getUtility(IBinaryPackageBuildSet)

        # Create a 386 builder
        self.builder = self.factory.makeBuilder()

        # Ensure that our builds were all built by the test builder.
        for build in self.builds:
            build.updateStatus(BuildStatus.FULLYBUILT, builder=self.builder)

    def test_getBuildsForBuilder_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForBuilder(self.builder.id)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForBuilder_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:2]
        builds = self.build_set.getBuildsForBuilder(self.builder.id,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)

    def test_getBuildsForBuilder_by_pocket(self):
        # Results can be filtered by pocket.
        builds = self.build_set.getBuildsForBuilder(
            self.builder.id, pocket=PackagePublishingPocket.RELEASE)
        self.assertContentEqual([self.builds[0], self.builds[2]], builds)
        builds = self.build_set.getBuildsForBuilder(
            self.builder.id, pocket=PackagePublishingPocket.PROPOSED)
        self.assertContentEqual([self.builds[1]], builds)


class TestBinaryPackageBuildWebservice(TestCaseWithFactory):
    """Test cases for BinaryPackageBuild on the webservice.

    NB. Note that most tests are currently in
    lib/lp/soyuz/stories/webservice/xx-builds.txt but unit tests really
    ought to be here instead.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBinaryPackageBuildWebservice, self).setUp()
        self.ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.build = self.factory.makeBinaryPackageBuild(archive=self.ppa)
        self.webservice = webservice_for_person(
            self.ppa.owner, permission=OAuthPermission.WRITE_PUBLIC)
        login(ANONYMOUS)

    def test_can_be_cancelled_is_exported(self):
        # Check that the can_be_cancelled property is exported.
        expected = self.build.can_be_cancelled
        entry_url = api_url(self.build)
        logout()
        entry = self.webservice.get(entry_url, api_version='devel').jsonBody()
        self.assertEqual(expected, entry['can_be_cancelled'])

    def test_cancel_is_exported(self):
        # Check that the cancel() named op is exported.
        build_url = api_url(self.build)
        self.build.queueBuild()
        logout()
        entry = self.webservice.get(build_url, api_version='devel').jsonBody()
        response = self.webservice.named_post(
            entry['self_link'], 'cancel', api_version='devel')
        self.assertEqual(200, response.status)
        entry = self.webservice.get(build_url, api_version='devel').jsonBody()
        self.assertEqual(BuildStatus.CANCELLED.title, entry['buildstate'])

    def test_cancel_security(self):
        # Check that unauthorised users cannot call cancel()
        build_url = api_url(self.build)
        webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        logout()

        entry = webservice.get(build_url, api_version='devel').jsonBody()
        response = webservice.named_post(
            entry['self_link'], 'cancel', api_version='devel')
        self.assertEqual(401, response.status)

    def test_builder_is_exported(self):
        # The builder property is exported.
        self.build.updateStatus(
            BuildStatus.FULLYBUILT, builder=self.factory.makeBuilder())
        build_url = api_url(self.build)
        builder_url = api_url(self.build.builder)
        logout()
        entry = self.webservice.get(build_url, api_version='devel').jsonBody()
        self.assertEndsWith(entry['builder_link'], builder_url)

    def test_source_package_name(self):
        name = self.build.source_package_release.name
        build_url = api_url(self.build)
        logout()
        entry = self.webservice.get(build_url, api_version='devel').jsonBody()
        self.assertEqual(name, entry['source_package_name'])


class TestPostprocessCandidate(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeBuildJob(self, pocket="RELEASE"):
        build = self.factory.makeBinaryPackageBuild(pocket=pocket)
        return build.queueBuild()

    def test_release_job(self):
        job = self.makeBuildJob()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        self.assertTrue(BinaryPackageBuildSet.postprocessCandidate(job, None))
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)

    def test_security_job_is_failed(self):
        job = self.makeBuildJob(pocket="SECURITY")
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        BinaryPackageBuildSet.postprocessCandidate(job, DevNullLogger())
        self.assertEqual(BuildStatus.FAILEDTOBUILD, build.status)

    def test_obsolete_job_without_flag_is_failed(self):
        job = self.makeBuildJob()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        distroseries = build.distro_arch_series.distroseries
        removeSecurityProxy(distroseries).status = SeriesStatus.OBSOLETE
        BinaryPackageBuildSet.postprocessCandidate(job, DevNullLogger())
        self.assertEqual(BuildStatus.FAILEDTOBUILD, build.status)

    def test_obsolete_job_with_flag_is_not_failed(self):
        job = self.makeBuildJob()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(job)
        distroseries = build.distro_arch_series.distroseries
        archive = build.archive
        removeSecurityProxy(distroseries).status = SeriesStatus.OBSOLETE
        removeSecurityProxy(archive).permit_obsolete_series_uploads = True
        BinaryPackageBuildSet.postprocessCandidate(job, DevNullLogger())
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)


class TestCalculateScore(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeBuild(self, purpose=None, private=False, component="main",
                  urgency="high", pocket="RELEASE", section_name=None):
        if purpose is not None or private:
            archive = self.factory.makeArchive(
                purpose=purpose, private=private)
        else:
            archive = None
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=archive, component=component, urgency=urgency,
            section_name=section_name)
        naked_spph = removeSecurityProxy(spph)  # needed for private archives
        return removeSecurityProxy(
            self.factory.makeBinaryPackageBuild(
                source_package_release=naked_spph.sourcepackagerelease,
                pocket=pocket))

    # The defaults for pocket, component, and urgency here match those in
    # makeBuildJob.
    def assertCorrectScore(self, build, pocket="RELEASE", component="main",
                           urgency="high", other_bonus=0):
        self.assertEqual(
            (SCORE_BY_POCKET[PackagePublishingPocket.items[pocket.upper()]] +
             SCORE_BY_COMPONENT[component] +
             SCORE_BY_URGENCY[SourcePackageUrgency.items[urgency.upper()]] +
             other_bonus), build.calculateScore())

    def test_score_unusual_component(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            component="unusual")
        build = self.factory.makeBinaryPackageBuild(
            source_package_release=spph.sourcepackagerelease)
        # For now just test that it doesn't raise an Exception
        build.calculateScore()

    def test_main_release_low_score(self):
        # 1500 (RELEASE) + 1000 (main) + 5 (low) = 2505.
        build = self.makeBuild(component="main", urgency="low")
        self.assertCorrectScore(build, "RELEASE", "main", "low")

    def test_copy_archive_main_release_low_score(self):
        # 1500 (RELEASE) + 1000 (main) + 5 (low) - 2600 (copy archive) = -95.
        # With this penalty, even language-packs and build retries will be
        # built before copy archives.
        build = self.makeBuild(
            purpose="COPY", component="main", urgency="low")
        self.assertCorrectScore(
            build, "RELEASE", "main", "low", -COPY_ARCHIVE_SCORE_PENALTY)

    def test_copy_archive_relative_score_is_applied(self):
        # Per-archive relative build scores are applied, in this case
        # exactly offsetting the copy-archive penalty.
        build = self.makeBuild(
            purpose="COPY", component="main", urgency="low")
        removeSecurityProxy(build.archive).relative_build_score = 2600
        self.assertCorrectScore(
            build, "RELEASE", "main", "low",
            -COPY_ARCHIVE_SCORE_PENALTY + 2600)

    def test_archive_negative_relative_score_is_applied(self):
        # Negative per-archive relative build scores are allowed.
        build = self.makeBuild(component="main", urgency="low")
        removeSecurityProxy(build.archive).relative_build_score = -100
        self.assertCorrectScore(build, "RELEASE", "main", "low", -100)

    def test_private_archive_bonus_is_applied(self):
        # Private archives get a bonus of 10000.
        build = self.makeBuild(private=True, component="main", urgency="high")
        self.assertCorrectScore(
            build, "RELEASE", "main", "high", PRIVATE_ARCHIVE_SCORE_BONUS)

    def test_main_release_low_recent_score(self):
        # 1500 (RELEASE) + 1000 (main) + 5 (low) = 2505.
        build = self.makeBuild(component="main", urgency="low")
        self.assertCorrectScore(build, "RELEASE", "main", "low")

    def test_universe_release_high_five_minutes_score(self):
        # 1500 (RELEASE) + 250 (universe) + 15 (high) = 1765.
        build = self.makeBuild(component="universe", urgency="high")
        self.assertCorrectScore(build, "RELEASE", "universe", "high")

    def test_multiverse_release_medium_fifteen_minutes_score(self):
        # 1500 (RELEASE) + 0 (multiverse) + 10 (medium) = 1510.
        build = self.makeBuild(component="multiverse", urgency="medium")
        self.assertCorrectScore(build, "RELEASE", "multiverse", "medium")

    def test_main_release_emergency_thirty_minutes_score(self):
        # 1500 (RELEASE) + 1000 (main) + 20 (emergency) = 2520.
        build = self.makeBuild(component="main", urgency="emergency")
        self.assertCorrectScore(build, "RELEASE", "main", "emergency")

    def test_restricted_release_low_one_hour_score(self):
        # 1500 (RELEASE) + 750 (restricted) + 5 (low) = 2255.
        build = self.makeBuild(component="restricted", urgency="low")
        self.assertCorrectScore(build, "RELEASE", "restricted", "low")

    def test_backports_score(self):
        # BACKPORTS is the lowest-priority pocket.
        build = self.makeBuild(pocket="BACKPORTS")
        self.assertCorrectScore(build, "BACKPORTS")

    def test_release_score(self):
        # RELEASE ranks next above BACKPORTS.
        build = self.makeBuild(pocket="RELEASE")
        self.assertCorrectScore(build, "RELEASE")

    def test_proposed_updates_score(self):
        # PROPOSED and UPDATES both rank next above RELEASE.  The reason why
        # PROPOSED and UPDATES have the same priority is because sources in
        # both pockets are submitted to the same policy and should reach
        # their audience as soon as possible (see more information about
        # this decision in bug #372491).
        proposed_build = self.makeBuild(pocket="PROPOSED")
        self.assertCorrectScore(proposed_build, "PROPOSED")
        updates_build = self.makeBuild(pocket="UPDATES")
        self.assertCorrectScore(updates_build, "UPDATES")

    def test_security_updates_score(self):
        # SECURITY is the top-ranked pocket.
        build = self.makeBuild(pocket="SECURITY")
        self.assertCorrectScore(build, "SECURITY")

    def test_score_packageset(self):
        # Package sets alter the score of official packages for their
        # series.
        build = self.makeBuild(
            component="main", urgency="low", purpose=ArchivePurpose.PRIMARY)
        packageset = self.factory.makePackageset(
            distroseries=build.distro_series)
        removeSecurityProxy(packageset).add(
            [build.source_package_release.sourcepackagename])
        removeSecurityProxy(packageset).relative_build_score = 100
        self.assertCorrectScore(build, "RELEASE", "main", "low", 100)

    def test_score_packageset_in_ppa(self):
        # Package set score boosts don't affect PPA packages.
        build = self.makeBuild(
            component="main", urgency="low", purpose=ArchivePurpose.PPA)
        packageset = self.factory.makePackageset(
            distroseries=build.distro_series)
        removeSecurityProxy(packageset).add(
            [build.source_package_release.sourcepackagename])
        removeSecurityProxy(packageset).relative_build_score = 100
        self.assertCorrectScore(build, "RELEASE", "main", "low", 0)

    def test_translations_score(self):
        # Language packs (the translations section) don't get any
        # package-specific score bumps. They always have the archive's
        # base score.
        build = self.makeBuild(section_name='translations')
        removeSecurityProxy(build.archive).relative_build_score = 666
        self.assertEqual(666, build.calculateScore())

    def assertScoreReadableByAnyone(self, obj):
        """An object's build score is readable by anyone."""
        with person_logged_in(obj.owner):
            obj_url = api_url(obj)
        removeSecurityProxy(obj).relative_build_score = 100
        webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        entry = webservice.get(obj_url, api_version="devel").jsonBody()
        self.assertEqual(100, entry["relative_build_score"])

    def assertScoreNotWriteableByOwner(self, obj):
        """Being an object's owner does not allow changing its build score.

        This affects a site-wide resource, and is thus restricted to
        launchpad-buildd-admins.
        """
        with person_logged_in(obj.owner):
            obj_url = api_url(obj)
        webservice = webservice_for_person(
            obj.owner, permission=OAuthPermission.WRITE_PUBLIC)
        entry = webservice.get(obj_url, api_version="devel").jsonBody()
        response = webservice.patch(
            entry["self_link"], "application/json",
            dumps(dict(relative_build_score=100)))
        self.assertEqual(401, response.status)
        new_entry = webservice.get(obj_url, api_version="devel").jsonBody()
        self.assertEqual(0, new_entry["relative_build_score"])

    def assertScoreWriteableByTeam(self, obj, team):
        """Members of TEAM can change an object's build score."""
        with person_logged_in(obj.owner):
            obj_url = api_url(obj)
        person = self.factory.makePerson(member_of=[team])
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        entry = webservice.get(obj_url, api_version="devel").jsonBody()
        response = webservice.patch(
            entry["self_link"], "application/json",
            dumps(dict(relative_build_score=100)))
        self.assertEqual(209, response.status)
        self.assertEqual(100, response.jsonBody()["relative_build_score"])

    def test_score_packageset_readable(self):
        # A packageset's build score is readable by anyone.
        packageset = self.factory.makePackageset()
        self.assertScoreReadableByAnyone(packageset)

    def test_score_packageset_forbids_non_buildd_admin(self):
        # Being the owner of a packageset is not enough to allow changing
        # its build score, since this affects a site-wide resource.
        packageset = self.factory.makePackageset()
        self.assertScoreNotWriteableByOwner(packageset)

    def test_score_packageset_allows_buildd_admin(self):
        # Buildd admins can change a packageset's build score.
        packageset = self.factory.makePackageset()
        self.assertScoreWriteableByTeam(
            packageset, getUtility(ILaunchpadCelebrities).buildd_admin)

    def test_score_archive_readable(self):
        # An archive's build score is readable by anyone.
        archive = self.factory.makeArchive()
        self.assertScoreReadableByAnyone(archive)

    def test_score_archive_forbids_non_buildd_admin(self):
        # Being the owner of an archive is not enough to allow changing its
        # build score, since this affects a site-wide resource.
        archive = self.factory.makeArchive()
        self.assertScoreNotWriteableByOwner(archive)

    def test_score_archive_allows_buildd_and_ppa_admin(self):
        # Buildd and PPA admins can change an archive's build score.
        archive = self.factory.makeArchive()
        self.assertScoreWriteableByTeam(
            archive, getUtility(ILaunchpadCelebrities).buildd_admin)
        with anonymous_logged_in():
            self.assertScoreWriteableByTeam(
                archive, getUtility(ILaunchpadCelebrities).ppa_admin)
