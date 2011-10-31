# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import IBuilderSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.tests.mock_slaves import WaitingSlave
from lp.buildmaster.tests.test_packagebuild import (
    TestGetUploadMethodsMixin,
    TestHandleStatusMixin,
    )
from lp.services.job.model.job import Job
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.binarypackagebuild import (
    IBinaryPackageBuild,
    IBinaryPackageBuildSet,
    UnparsableDependencies,
    )
from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    api_url,
    logout,
    TestCaseWithFactory,
    )


class TestBinaryPackageBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBinaryPackageBuild, self).setUp()
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        gedit_spph = publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        gedit_spr = gedit_spph.sourcepackagerelease
        self.build = gedit_spr.createBuild(
            distro_arch_series=publisher.distroseries['i386'],
            archive=gedit_spr.upload_archive,
            pocket=gedit_spr.package_upload.pocket)

    def test_providesInterfaces(self):
        # Build provides IPackageBuild and IBuild.
        self.assertProvides(self.build, IPackageBuild)
        self.assertProvides(self.build, IBinaryPackageBuild)

    def test_queueBuild(self):
        # BinaryPackageBuild can create the queue entry for itself.
        bq = self.build.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertProvides(bq.specific_job, IBuildPackageJob)
        self.failUnlessEqual(self.build.is_virtualized, bq.virtualized)
        self.failIfEqual(None, bq.processor)
        self.failUnless(bq, self.build.buildqueue_record)

    def test_getBuildCookie(self):
        # A build cookie is made up of the job type and record id.
        # The uploadprocessor relies on this format.
        Store.of(self.build).flush()
        cookie = self.build.getBuildCookie()
        expected_cookie = "PACKAGEBUILD-%d" % self.build.id
        self.assertEquals(expected_cookie, cookie)

    def test_estimateDuration(self):
        # Without previous builds, a negligable package size estimate is 60s
        self.assertEqual(60, self.build.estimateDuration().seconds)

    def create_previous_build(self, duration):
        spr = self.build.source_package_release
        build = spr.createBuild(
            distro_arch_series=self.build.distro_arch_series,
            archive=spr.upload_archive, pocket=spr.package_upload.pocket)
        build.status = BuildStatus.FULLYBUILT
        now = datetime.now(pytz.UTC)
        build.date_finished = now
        build.date_started = now - timedelta(seconds=duration)
        return build

    def test_estimateDuration_with_history(self):
        # Previous builds of the same source are used for estimates.
        self.create_previous_build(335)
        self.assertEqual(335, self.build.estimateDuration().seconds)

    def addFakeBuildLog(self):
        lfa = self.factory.makeLibraryFileAlias('mybuildlog.txt')
        removeSecurityProxy(self.build).log = lfa

    def test_log_url(self):
        # The log URL for a binary package build will use
        # the distribution source package release when the context
        # is not a PPA or a copy archive.
        self.addFakeBuildLog()
        self.failUnlessEqual(
            'http://launchpad.dev/ubuntutest/+source/'
            'gedit/666/+build/%d/+files/mybuildlog.txt' % (
                self.build.package_build.build_farm_job.id),
            self.build.log_url)

    def test_log_url_ppa(self):
        # On the other hand, ppa or copy builds will have a url in the
        # context of the archive.
        self.addFakeBuildLog()
        ppa_owner = self.factory.makePerson(name="joe")
        removeSecurityProxy(self.build).archive = self.factory.makeArchive(
            owner=ppa_owner, name="myppa")
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/myppa/+build/%d/+files/mybuildlog.txt' % (
                self.build.build_farm_job.id),
            self.build.log_url)

    def test_adapt_from_build_farm_job(self):
        # An `IBuildFarmJob` can be adapted to an IBinaryPackageBuild
        # if it has the correct job type.
        build_farm_job = self.build.build_farm_job
        store = Store.of(build_farm_job)
        store.flush()

        self.failUnlessEqual(self.build, build_farm_job.getSpecificJob())

    def test_adapt_from_build_farm_job_prefetching(self):
        # The package_build is prefetched for efficiency.
        build_farm_job = self.build.build_farm_job

        # We clear the cache to avoid getting cached objects where
        # they would normally be queries.
        store = Store.of(build_farm_job)
        store.flush()
        store.invalidate()

        binary_package_build = build_farm_job.getSpecificJob()

        self.assertStatementCount(
            0, getattr, binary_package_build, "package_build")
        self.assertStatementCount(
            0, getattr, binary_package_build, "build_farm_job")

    def test_getSpecificJob_noop(self):
        # If getSpecificJob is called on the binary build it is a noop.
        store = Store.of(self.build)
        store.flush()
        self.assertStatementCount(
            0, self.build.getSpecificJob)

    def test_getUploader(self):
        # For ACL purposes the uploader is the changes file signer.

        class MockChanges:
            signer = "Somebody <somebody@ubuntu.com>"

        self.assertEquals("Somebody <somebody@ubuntu.com>",
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
        # Only virtual builds can be cancelled.
        bq = removeSecurityProxy(self.build.queueBuild())
        bq.virtualized = True
        self.assertTrue(self.build.can_be_cancelled)
        bq.virtualized = False
        self.assertFalse(self.build.can_be_cancelled)


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
        depwait_build.status = BuildStatus.MANUALDEPWAIT
        depwait_build.dependencies = u'dep-bin'

        return depwait_build

    def testBuildqueueRemoval(self):
        """Test removing buildqueue items.

        Removing a Buildqueue row should also remove its associated
        BuildPackageJob and Job rows.
        """
        # Create a build in depwait.
        depwait_build = self._setupSimpleDepwaitContext()
        depwait_build_id = depwait_build.id

        # Grab the relevant db records for later comparison.
        store = Store.of(depwait_build)
        build_package_job = store.find(
            BuildPackageJob,
            depwait_build.id == BuildPackageJob.build).one()
        build_package_job_id = build_package_job.id
        job_id = store.find(Job, Job.id == build_package_job.job.id).one().id
        build_queue_id = store.find(
            BuildQueue, BuildQueue.job == job_id).one().id

        depwait_build.buildqueue_record.destroySelf()

        # Test that the records above no longer exist in the db.
        self.assertEqual(
            store.find(
                BuildPackageJob,
                BuildPackageJob.id == build_package_job_id).count(),
            0)
        self.assertEqual(
            store.find(Job, Job.id == job_id).count(),
            0)
        self.assertEqual(
            store.find(BuildQueue, BuildQueue.id == build_queue_id).count(),
            0)
        # But the build itself still exists.
        self.assertEqual(
            store.find(
                BinaryPackageBuild,
                BinaryPackageBuild.id == depwait_build_id).count(),
            1)

    def testUpdateDependenciesWorks(self):
        # Calling `IBinaryPackageBuild.updateDependencies` makes the build
        # record ready for dispatch.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, '')

    def testInvalidDependencies(self):
        # Calling `IBinaryPackageBuild.updateDependencies` on a build with
        # invalid 'dependencies' raises an AssertionError.
        # Anything not following '<name> [([relation] <version>)][, ...]'
        depwait_build = self._setupSimpleDepwaitContext()

        # None is not a valid dependency values.
        depwait_build.dependencies = None
        self.assertRaises(
            UnparsableDependencies, depwait_build.updateDependencies)

        # Missing 'name'.
        depwait_build.dependencies = u'(>> version)'
        self.assertRaises(
            UnparsableDependencies, depwait_build.updateDependencies)

        # Missing 'version'.
        depwait_build.dependencies = u'name (>>)'
        self.assertRaises(
            UnparsableDependencies, depwait_build.updateDependencies)

        # Missing comman between dependencies.
        depwait_build.dependencies = u'name1 name2'
        self.assertRaises(
            UnparsableDependencies, depwait_build.updateDependencies)

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
        self.assertEquals(depwait_build.dependencies, '')

    def testVersionedDependencies(self):
        # `IBinaryPackageBuild.updateDependencies` supports versioned
        # dependencies. A build will not be retried unless the candidate
        # complies with the version restriction.
        # In this case, dep-bin 666 is available. >> 666 isn't
        # satisified, but >= 666 is.
        depwait_build = self._setupSimpleDepwaitContext()
        self.layer.txn.commit()

        depwait_build.dependencies = u'dep-bin (>> 666)'
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, u'dep-bin (>> 666)')
        depwait_build.dependencies = u'dep-bin (>= 666)'
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, u'')

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

        depwait_build.dependencies = u'dep-bin (= 666)'
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, u'')
        depwait_build.dependencies = u'dep-bin (= 999)'
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, u'')


class BaseTestCaseWithThreeBuilds(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some builds for the test archive."""
        super(BaseTestCaseWithThreeBuilds, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create three builds for the publisher's default
        # distroseries.
        self.builds = []
        self.sources = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.builds += gedit_src_hist.createMissingBuilds()
        self.sources.append(gedit_src_hist)

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED)
        self.builds += firefox_src_hist.createMissingBuilds()
        self.sources.append(firefox_src_hist)

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            status=PackagePublishingStatus.PUBLISHED)
        self.builds += gtg_src_hist.createMissingBuilds()
        self.sources.append(gtg_src_hist)


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
        self.assertIs(
            None,
            getUtility(IBinaryPackageBuildSet).getByBuildFarmJob(
                sprb.build_farm_job))


class TestBuildSetGetBuildsForArchive(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestBuildSetGetBuildsForArchive, self).setUp()

        # Short-cuts for our tests.
        self.archive = self.publisher.distroseries.main_archive
        self.build_set = getUtility(IBinaryPackageBuildSet)

    def test_getBuildsForArchive_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForArchive(self.archive)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForArchive_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        removeSecurityProxy(hppa_build).distro_arch_series = (
            self.publisher.distroseries['hppa'])

        builds = self.build_set.getBuildsForArchive(self.archive,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)


class TestBuildSetGetBuildsForBuilder(BaseTestCaseWithThreeBuilds):

    def setUp(self):
        super(TestBuildSetGetBuildsForBuilder, self).setUp()

        # Short-cuts for our tests.
        self.build_set = getUtility(IBinaryPackageBuildSet)

        # Create a 386 builder
        owner = self.factory.makePerson()
        processor_family = ProcessorFamilySet().getByProcessorName('386')
        processor = processor_family.processors[0]
        builder_set = getUtility(IBuilderSet)

        self.builder = builder_set.new(
            processor, 'http://example.com', 'Newbob', 'New Bob the Builder',
            'A new and improved bob.', owner)

        # Ensure that our builds were all built by the test builder.
        for build in self.builds:
            build.builder = self.builder

    def test_getBuildsForBuilder_no_params(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForBuilder(self.builder.id)
        self.assertContentEqual(builds, self.builds)

    def test_getBuildsForBuilder_by_arch_tag(self):
        # Results can be filtered by architecture tag.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        removeSecurityProxy(hppa_build).distro_arch_series = (
            self.publisher.distroseries['hppa'])

        builds = self.build_set.getBuildsForBuilder(self.builder.id,
                                                    arch_tag="i386")
        self.assertContentEqual(builds, i386_builds)


class TestStoreBuildInfo(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestStoreBuildInfo, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.build = gedit_src_hist.createMissingBuilds()[0]

        self.builder = self.factory.makeBuilder()
        self.builder.setSlaveForTesting(WaitingSlave('BuildStatus.OK'))
        self.build.buildqueue_record.markAsBuilding(self.builder)

    def testDependencies(self):
        """Verify that storeBuildInfo sets any dependencies."""
        self.build.storeBuildInfo(
            self.build, None, {'dependencies': 'somepackage'})
        self.assertIsNot(None, self.build.log)
        self.assertEqual(self.builder, self.build.builder)
        self.assertEqual(u'somepackage', self.build.dependencies)

    def testWithoutDependencies(self):
        """Verify that storeBuildInfo clears the build's dependencies."""
        # Set something just to make sure that storeBuildInfo actually
        # empties it.
        self.build.dependencies = u'something'
        self.build.storeBuildInfo(self.build, None, {})
        self.assertIsNot(None, self.build.log)
        self.assertEqual(self.builder, self.build.builder)
        self.assertIs(None, self.build.dependencies)
        self.assertIsNot(None, self.build.date_finished)

    def test_sets_date_finished(self):
        # storeBuildInfo should set date_finished on the BuildFarmJob.
        self.assertIs(None, self.build.date_finished)
        self.build.storeBuildInfo(self.build, None, {})
        self.assertIsNot(None, self.build.date_finished)


class MakeBinaryPackageBuildMixin:
    """Provide the makeBuild method returning a queud build."""

    def makeBuild(self):
        test_publisher = SoyuzTestPublisher()
        test_publisher.prepareBreezyAutotest()
        binaries = test_publisher.getPubBinaries()
        return binaries[0].binarypackagerelease.build


class TestGetUploadMethodsForBinaryPackageBuild(
    MakeBinaryPackageBuildMixin, TestGetUploadMethodsMixin,
    TestCaseWithFactory):
    """IPackageBuild.getUpload-related methods work with binary builds."""


class TestHandleStatusForBinaryPackageBuild(
    MakeBinaryPackageBuildMixin, TestHandleStatusMixin, TrialTestCase):
    """IPackageBuild.handleStatus works with binary builds."""


class TestBinaryPackageBuildWebservice(TestCaseWithFactory):
    """Test cases for BinaryPackageBuild on the webservice.

    NB. Note that most tests are currently in
    lib/lp/soyuz/stories/webservice/xx-builds.txt but unit tests really
    ought to be here instead.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBinaryPackageBuildWebservice, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_exports_can_be_cancelled(self):
        build = self.factory.makeBinaryPackageBuild()
        expected = build.can_be_cancelled
        entry_url = api_url(build)
        logout()
        entry = self.webservice.get(
            entry_url, api_version='devel').jsonBody()
        self.assertEqual(expected, entry['can_be_cancelled'])

