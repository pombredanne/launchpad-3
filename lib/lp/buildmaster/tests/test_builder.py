# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Builder features."""

from __future__ import absolute_import, print_function, unicode_literals

from fixtures import FakeLogger
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuilderCleanStatus,
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.tests.mock_slaves import make_publisher
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import flush_database_updates
from lp.services.features.testing import FeatureFixture
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.testing import (
    admin_logged_in,
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestBuilder(TestCaseWithFactory):
    """Basic unit tests for `Builder`."""

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        # Builder provides IBuilder
        builder = self.factory.makeBuilder()
        with celebrity_logged_in('buildd_admin'):
            self.assertProvides(builder, IBuilder)

    def test_default_values(self):
        builder = self.factory.makeBuilder()
        # Make sure the Storm cache gets the values that the database
        # initializes.
        flush_database_updates()
        self.assertEqual(0, builder.failure_count)

    def test_setting_builderok_resets_failure_count(self):
        builder = removeSecurityProxy(self.factory.makeBuilder())
        builder.failure_count = 1
        builder.builderok = False
        self.assertEqual(1, builder.failure_count)
        builder.builderok = True
        self.assertEqual(0, builder.failure_count)

    def test_setting_builderok_dirties(self):
        builder = removeSecurityProxy(self.factory.makeBuilder())
        builder.builderok = False
        builder.setCleanStatus(BuilderCleanStatus.CLEAN)
        builder.builderok = True
        self.assertEqual(BuilderCleanStatus.DIRTY, builder.clean_status)

    def test_setCleanStatus(self):
        builder = self.factory.makeBuilder()
        self.assertEqual(BuilderCleanStatus.DIRTY, builder.clean_status)
        with celebrity_logged_in('buildd_admin'):
            builder.setCleanStatus(BuilderCleanStatus.CLEAN)
        self.assertEqual(BuilderCleanStatus.CLEAN, builder.clean_status)

    def test_set_processors(self):
        builder = self.factory.makeBuilder()
        proc1 = self.factory.makeProcessor()
        proc2 = self.factory.makeProcessor()
        with admin_logged_in():
            builder.processors = [proc1, proc2]
        self.assertEqual(proc1, builder.processor)
        self.assertEqual([proc1, proc2], builder.processors)

    def test_set_processor(self):
        builder = self.factory.makeBuilder()
        proc = self.factory.makeProcessor()
        with admin_logged_in():
            builder.processor = proc
        self.assertEqual(proc, builder.processor)
        self.assertEqual([proc], builder.processors)


class TestFindBuildCandidateBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidateBase, self).setUp()
        self.publisher = make_publisher()
        self.publisher.prepareBreezyAutotest()

        # Create some i386 builders ready to build PPA builds.  Two
        # already exist in sampledata so we'll use those first.
        self.builder1 = getUtility(IBuilderSet)['bob']
        self.frog_builder = getUtility(IBuilderSet)['frog']
        self.builder3 = self.factory.makeBuilder(name='builder3')
        self.builder4 = self.factory.makeBuilder(name='builder4')
        self.builder5 = self.factory.makeBuilder(name='builder5')
        self.builders = [
            self.builder1,
            self.frog_builder,
            self.builder3,
            self.builder4,
            self.builder5,
            ]

        # Ensure all builders are operational.
        for builder in self.builders:
            builder.builderok = True
            builder.manual = False


class TestFindBuildCandidateGeneralCases(TestFindBuildCandidateBase):
    # Test usage of findBuildCandidate not specific to any archive type.

    def test_findBuildCandidate_matches_processor(self):
        # Builder._findBuildCandidate returns the highest scored build
        # for any of the builder's architectures.
        bq1 = self.factory.makeBinaryPackageBuild().queueBuild()
        bq2 = self.factory.makeBinaryPackageBuild().queueBuild()

        # With no job for the builder's processor, no job is returned.
        proc = self.factory.makeProcessor()
        builder = removeSecurityProxy(
            self.factory.makeBuilder(processors=[proc], virtualized=True))
        self.assertIs(None, builder._findBuildCandidate())

        # Once bq1's processor is added to the mix, it's the best
        # candidate.
        builder.processors = [proc, bq1.processor]
        self.assertEqual(bq1, builder._findBuildCandidate())

        # bq2's score doesn't matter, as its processor isn't suitable
        # for our builder.
        bq2.manualScore(3000)
        self.assertEqual(bq1, builder._findBuildCandidate())

        # But once we add bq2's processor, its higher score makes it win.
        builder.processors = [bq1.processor, bq2.processor]
        self.assertEqual(bq2, builder._findBuildCandidate())

    def test_findBuildCandidate_supersedes_builds(self):
        # IBuilder._findBuildCandidate identifies if there are builds
        # for superseded source package releases in the queue and marks
        # the corresponding build record as SUPERSEDED.
        archive = self.factory.makeArchive()
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=archive).createMissingBuilds()
        old_candidate = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        # The candidate starts off as NEEDSBUILD:
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(
            old_candidate)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)

        # Now supersede the source package:
        publication = build.current_source_publication
        publication.status = PackagePublishingStatus.SUPERSEDED

        # The candidate returned is now a different one:
        new_candidate = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        self.assertNotEqual(new_candidate, old_candidate)

        # And the old_candidate is superseded:
        self.assertEqual(BuildStatus.SUPERSEDED, build.status)

    def test_findBuildCandidate_honours_minimum_score(self):
        # Sometimes there's an emergency that requires us to lock down the
        # build farm except for certain whitelisted builds.  We do this by
        # way of a feature flag to set a minimum score; if this is set,
        # Builder._findBuildCandidate will ignore any build with a lower
        # score.
        bq1 = self.factory.makeBinaryPackageBuild().queueBuild()
        bq1.manualScore(100000)
        bq2 = self.factory.makeBinaryPackageBuild().queueBuild()
        bq2.manualScore(99999)
        builder1 = removeSecurityProxy(
            self.factory.makeBuilder(
                processors=[bq1.processor, self.factory.makeProcessor()],
                virtualized=True))
        builder2 = removeSecurityProxy(
            self.factory.makeBuilder(
                processors=[bq2.processor, self.factory.makeProcessor()],
                virtualized=True))

        # By default, each builder has the appropriate one of the two builds
        # we just created as a candidate.
        self.assertEqual(bq1, builder1._findBuildCandidate())
        self.assertEqual(bq2, builder2._findBuildCandidate())

        # If we set a minimum score, then only builds above that threshold
        # are candidates.
        with FeatureFixture({'buildmaster.minimum_score': '100000'}):
            self.assertEqual(bq1, builder1._findBuildCandidate())
            self.assertIsNone(builder2._findBuildCandidate())

        # We can similarly set a minimum score for individual processors.
        # The maximum of these for any processor supported by the builder is
        # used.
        cases = [
            ({0: '99999'}, bq2),
            ({1: '99999'}, bq2),
            ({0: '100000'}, None),
            ({1: '100000'}, None),
            ({0: '99999', 1: '99999'}, bq2),
            ({0: '99999', 1: '100000'}, None),
            ({0: '100000', 1: '99999'}, None),
            ]
        for feature_spec, expected_bq in cases:
            features = {
                'buildmaster.minimum_score.%s' % builder2.processors[i].name:
                    score
                for i, score in feature_spec.items()}
            with FeatureFixture(features):
                self.assertEqual(expected_bq, builder2._findBuildCandidate())

        # If we set an invalid minimum score, buildd-manager doesn't
        # explode.
        with FakeLogger() as logger:
            with FeatureFixture({'buildmaster.minimum_score': 'nonsense'}):
                self.assertEqual(bq1, builder1._findBuildCandidate())
                self.assertEqual(bq2, builder2._findBuildCandidate())
            self.assertEqual(
                "invalid buildmaster.minimum_score u'nonsense'\n"
                "invalid buildmaster.minimum_score u'nonsense'\n",
                logger.output)

    def test_acquireBuildCandidate_marks_building(self):
        # acquireBuildCandidate() should call _findBuildCandidate and
        # mark the build as building.
        archive = self.factory.makeArchive()
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=archive).createMissingBuilds()
        candidate = removeSecurityProxy(
            self.frog_builder).acquireBuildCandidate()
        self.assertEqual(BuildQueueStatus.RUNNING, candidate.status)


class TestFindBuildCandidatePPAWithSingleBuilder(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidatePPAWithSingleBuilder, self).setUp()
        self.publisher = make_publisher()
        self.publisher.prepareBreezyAutotest()

        self.bob_builder = getUtility(IBuilderSet)['bob']
        self.frog_builder = getUtility(IBuilderSet)['frog']

        # Disable bob so only frog is available.
        self.bob_builder.manual = True
        self.bob_builder.builderok = True
        self.frog_builder.manual = False
        self.frog_builder.builderok = True

        # Make a new PPA and give it some builds.
        self.ppa_joe = self.factory.makeArchive(name="joesppa")
        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()

    def test_findBuildCandidate_first_build_started(self):
        # The allocation rule for PPA dispatching doesn't apply when
        # there's only one builder available.

        # Asking frog to find a candidate should give us the joesppa build.
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)

        # If bob is in a failed state the joesppa build is still
        # returned.
        self.bob_builder.builderok = False
        self.bob_builder.manual = False
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)


class TestFindBuildCandidatePPABase(TestFindBuildCandidateBase):

    ppa_joe_private = False
    ppa_jim_private = False

    def _setBuildsBuildingForArch(self, builds_list, num_builds,
                                  archtag="i386"):
        """Helper function.

        Set the first `num_builds` in `builds_list` with `archtag` as
        BUILDING.
        """
        count = 0
        for build in builds_list[:num_builds]:
            if build.distro_arch_series.architecturetag == archtag:
                build.updateStatus(
                    BuildStatus.BUILDING, builder=self.builders[count])
            count += 1

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidatePPABase, self).setUp()

        # Create two PPAs and add some builds to each.
        self.ppa_joe = self.factory.makeArchive(
            name="joesppa", private=self.ppa_joe_private)
        self.ppa_jim = self.factory.makeArchive(
            name="jimsppa", private=self.ppa_jim_private)

        self.joe_builds = []
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="cobblers",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())
        self.joe_builds.extend(
            self.publisher.getPubSource(
                sourcename="thunderpants",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_joe).createMissingBuilds())

        self.jim_builds = []
        self.jim_builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_jim).createMissingBuilds())
        self.jim_builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.ppa_jim).createMissingBuilds())

        # Set the first three builds in joe's PPA as building, which
        # leaves two builders free.
        self._setBuildsBuildingForArch(self.joe_builds, 3)
        num_active_builders = len(
            [build for build in self.joe_builds if build.builder is not None])
        num_free_builders = len(self.builders) - num_active_builders
        self.assertEqual(num_free_builders, 2)


class TestFindBuildCandidatePPA(TestFindBuildCandidatePPABase):

    def test_findBuildCandidate(self):
        # joe's fourth i386 build will be the next build candidate.
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)

    def test_findBuildCandidate_with_disabled_archive(self):
        # Disabled archives should not be considered for dispatching
        # builds.
        disabled_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(
            disabled_job)
        build.archive.disable()
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        self.assertNotEqual(disabled_job, next_job)


class TestFindBuildCandidatePrivatePPA(TestFindBuildCandidatePPABase):

    ppa_joe_private = True

    def test_findBuildCandidate_for_private_ppa(self):
        # joe's fourth i386 build will be the next build candidate.
        next_job = removeSecurityProxy(self.builder4)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)

        # If the source for the build is still pending, it won't be
        # dispatched because the builder has to fetch the source files
        # from the (password protected) repo area, not the librarian.
        pub = build.current_source_publication
        pub.status = PackagePublishingStatus.PENDING
        candidate = removeSecurityProxy(self.builder4)._findBuildCandidate()
        self.assertNotEqual(next_job.id, candidate.id)


class TestFindBuildCandidateDistroArchive(TestFindBuildCandidateBase):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidateDistroArchive, self).setUp()
        # Create a primary archive and publish some builds for the
        # queue.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)

        self.gedit_build = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.non_ppa).createMissingBuilds()[0]
        self.firefox_build = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            archive=self.non_ppa).createMissingBuilds()[0]

    def test_findBuildCandidate_for_non_ppa(self):
        # Normal archives are not restricted to serial builds per
        # arch.

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('primary', build.archive.name)
        self.assertEqual('gedit', build.source_package_release.name)

        # Now even if we set the build building, we'll still get the
        # second non-ppa build for the same archive as the next candidate.
        build.updateStatus(BuildStatus.BUILDING, builder=self.frog_builder)
        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()
        build = getUtility(IBinaryPackageBuildSet).getByQueueEntry(next_job)
        self.assertEqual('primary', build.archive.name)
        self.assertEqual('firefox', build.source_package_release.name)

    def test_findBuildCandidate_for_recipe_build(self):
        # Recipe builds with a higher score are selected first.
        # This test is run in a context with mixed recipe and binary builds.

        self.assertIsNot(self.frog_builder.processor, None)
        self.assertEqual(self.frog_builder.virtualized, True)

        self.assertEqual(self.gedit_build.buildqueue_record.lastscore, 2505)
        self.assertEqual(self.firefox_build.buildqueue_record.lastscore, 2505)

        das = self.factory.makeDistroArchSeries(
            processor=getUtility(IProcessorSet).getByName('386'))
        das.distroseries.nominatedarchindep = das
        recipe_build_job = self.factory.makeSourcePackageRecipeBuild(
            distroseries=das.distroseries).queueBuild()
        recipe_build_job.manualScore(9999)

        self.assertEqual(recipe_build_job.lastscore, 9999)

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        self.assertEqual(recipe_build_job, next_job)


class TestFindRecipeBuildCandidates(TestFindBuildCandidateBase):
    # These tests operate in a "recipe builds only" setting.
    # Please see also bug #507782.

    def clearBuildQueue(self):
        """Delete all `BuildQueue`, XXXJOb and `Job` instances."""
        for bq in IStore(BuildQueue).find(BuildQueue):
            bq.destroySelf()

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindRecipeBuildCandidates, self).setUp()
        # Create a primary archive and publish some builds for the
        # queue.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)

        das = self.factory.makeDistroArchSeries(
            processor=getUtility(IProcessorSet).getByName('386'))
        das.distroseries.nominatedarchindep = das
        self.clearBuildQueue()
        self.bq1 = self.factory.makeSourcePackageRecipeBuild(
            distroseries=das.distroseries).queueBuild()
        self.bq1.manualScore(3333)
        self.bq2 = self.factory.makeSourcePackageRecipeBuild(
            distroseries=das.distroseries).queueBuild()
        self.bq2.manualScore(4333)

    def test_findBuildCandidate_with_highest_score(self):
        # The recipe build with the highest score is selected first.
        # This test is run in a "recipe builds only" context.

        self.assertIsNot(self.frog_builder.processor, None)
        self.assertEqual(self.frog_builder.virtualized, True)

        next_job = removeSecurityProxy(
            self.frog_builder)._findBuildCandidate()

        self.assertEqual(self.bq2, next_job)
