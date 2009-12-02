# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Builder features."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch, IBuildFarmJobBehavior)
from lp.buildmaster.model.buildfarmjobbehavior import IdleBuildBehavior
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.binarypackagebuildbehavior import (
    BinaryPackageBuildBehavior)
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestFindBuildCandidateBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidateBase, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create some i386 builders ready to build PPA builds.  Two
        # already exist in sampledata so we'll use those first.
        self.builder1 = getUtility(IBuilderSet)['bob']
        self.builder2 = getUtility(IBuilderSet)['frog']
        self.builder3 = self.factory.makeBuilder(name='builder3')
        self.builder4 = self.factory.makeBuilder(name='builder4')
        self.builder5 = self.factory.makeBuilder(name='builder5')
        self.builders = [
            self.builder1,
            self.builder2,
            self.builder3,
            self.builder4,
            self.builder5,
            ]

        # Ensure all builders are operational.
        for builder in self.builders:
            builder.builderok = True
            builder.manual = False


class TestFindBuildCandidatePPAWithSingleBuilder(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFindBuildCandidatePPAWithSingleBuilder, self).setUp()
        self.publisher = SoyuzTestPublisher()
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
        builds = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()

    def test_findBuildCandidate_first_build_started(self):
        # The allocation rule for PPA dispatching doesn't apply when
        # there's only one builder available.

        # Asking frog to find a candidate should give us the joesppa build.
        next_job = self.frog_builder.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)

        # If bob is in a failed state the joesppa build is still
        # returned.
        self.bob_builder.builderok = False
        self.bob_builder.manual = False
        next_job = self.frog_builder.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.assertEqual('joesppa', build.archive.name)


class TestFindBuildCandidatePPA(TestFindBuildCandidateBase):

    def _setBuildsBuildingForArch(self, builds_list, num_builds,
                                  archtag="i386"):
        """Helper function.

        Set the first `num_builds` in `builds_list` with `archtag` as
        BUILDING.
        """
        count = 0
        for build in builds_list[:num_builds]:
            if build.distroarchseries.architecturetag == archtag:
                build.buildstate = BuildStatus.BUILDING
                build.builder = self.builders[count]
            count += 1

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidatePPA, self).setUp()

        # Create two PPAs and add some builds to each.
        self.ppa_joe = self.factory.makeArchive(name="joesppa")
        self.ppa_jim = self.factory.makeArchive(name="jimsppa")

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

    def test_findBuildCandidate_first_build_started(self):
        # A PPA cannot start a build if it would use 80% or more of the
        # builders.
        next_job = self.builder4.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.failIfEqual('joesppa', build.archive.name)

    def test_findBuildCandidate_first_build_finished(self):
        # When joe's first ppa build finishes, his fourth i386 build
        # will be the next build candidate.
        self.joe_builds[0].buildstate = BuildStatus.FAILEDTOBUILD
        next_job = self.builder4.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('joesppa', build.archive.name)

    def test_findBuildCandidate_for_private_ppa(self):
        # If a ppa is private it will be able to have parallel builds
        # for the one architecture.
        self.ppa_joe.private = True
        self.ppa_joe.buildd_secret = 'sekrit'
        next_job = self.builder4.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('joesppa', build.archive.name)


class TestFindBuildCandidateDistroArchive(TestFindBuildCandidateBase):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidateDistroArchive, self).setUp()
        # Create a primary archive and publish some builds for the
        # queue.
        non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)

        gedit_build = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=non_ppa).createMissingBuilds()[0]
        firefox_build = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            archive=non_ppa).createMissingBuilds()[0]

    def test_findBuildCandidate_for_non_ppa(self):
        # Normal archives are not restricted to serial builds per
        # arch.

        next_job = self.builder2.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('primary', build.archive.name)
        self.failUnlessEqual('gedit', build.sourcepackagerelease.name)

        # Now even if we set the build building, we'll still get the
        # second non-ppa build for the same archive as the next candidate.
        build.buildstate = BuildStatus.BUILDING
        build.builder = self.builder2
        next_job = self.builder2.findBuildCandidate()
        build = getUtility(IBuildSet).getByQueueEntry(next_job)
        self.failUnlessEqual('primary', build.archive.name)
        self.failUnlessEqual('firefox', build.sourcepackagerelease.name)


class TestCurrentBuildBehavior(TestCaseWithFactory):
    """This test ensures the get/set behavior of IBuilder's
    current_build_behavior property.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create a new builder ready for testing."""
        super(TestCurrentBuildBehavior, self).setUp()
        self.builder = self.factory.makeBuilder(name='builder')

        # Have a publisher and a ppa handy for some of the tests below.
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.ppa_joe = self.factory.makeArchive(name="joesppa")

        self.build = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()[0]

        self.buildfarmjob = self.build.buildqueue_record.specific_job

    def test_idle_behavior_when_no_current_build(self):
        """We return an idle behavior when there is no behavior specified
        nor a current build.
        """
        self.assertIsInstance(
            self.builder.current_build_behavior, IdleBuildBehavior)

    def test_set_behavior_when_no_current_job(self):
        """If a builder is idle then it is possible to set the behavior."""
        self.builder.current_build_behavior = IBuildFarmJobBehavior(
            self.buildfarmjob)

        self.assertIsInstance(
            self.builder.current_build_behavior, BinaryPackageBuildBehavior)

    def test_current_job_behavior(self):
        """The current behavior is set automatically from the current job."""
        # Set the builder attribute on the buildqueue record so that our
        # builder will think it has a current build.
        self.build.buildqueue_record.builder = self.builder

        self.assertIsInstance(
            self.builder.current_build_behavior, BinaryPackageBuildBehavior)

    def test_set_behavior_when_current_job(self):
        """If a builder has a current job then it's behavior cannot be set.
        """
        self.build.buildqueue_record.builder = self.builder

        # As we can't use assertRaises for a property, we use a try-except
        # instead.
        assertion_raised = False
        try:
            self.builder.current_build_behavior = IBuildFarmJobBehavior(
                self.buildfarmjob)
        except BuildBehaviorMismatch, e:
            assertion_raised = True

        self.failUnless(assertion_raised)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
