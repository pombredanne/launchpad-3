# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test Build features."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestBuildUpdateDependencies(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def _setupSimpleDepwaitContext(self):
        """Use `SoyuzTestPublisher` to setup a simple depwait context.

        Return an `IBuild` in MANUALDEWAIT state and depending on a
        binary that exists and is reachable.
        """
        test_publisher = SoyuzTestPublisher()
        test_publisher.prepareBreezyAutotest()

        depwait_source = test_publisher.getPubSource(
            sourcename='depwait-source')

        test_publisher.getPubBinaries(
            binaryname='dep-bin',
            status=PackagePublishingStatus.PUBLISHED)

        [depwait_build] = depwait_source.createMissingBuilds()
        depwait_build.buildstate = BuildStatus.MANUALDEPWAIT
        depwait_build.dependencies = 'dep-bin'

        return depwait_build

    def testUpdateDependenciesWorks(self):
        # Calling `IBuild.updateDependencies` makes the build
        # record ready for dispatch.
        depwait_build = self._setupSimpleDepwaitContext()
        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, '')

    def testInvalidDependencies(self):
        # Calling `IBuild.updateDependencies` on a build with
        # invalid 'dependencies' raises an AssertionError.
        # Anything not following '<name> [([relation] <version>)][, ...]'
        depwait_build = self._setupSimpleDepwaitContext()

        # None is not a valid dependency values.
        depwait_build.dependencies = None
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing 'name'.
        depwait_build.dependencies = '(>> version)'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing 'version'.
        depwait_build.dependencies = 'name (>>)'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

        # Missing comman between dependencies.
        depwait_build.dependencies = 'name1 name2'
        self.assertRaises(
            AssertionError, depwait_build.updateDependencies)

    def testBug378828(self):
        # `IBuild.updateDependencies` copes with the scenario where
        # the corresponding source publication is not active (deleted)
        # and the source original component is not a valid ubuntu
        # component.
        depwait_build = self._setupSimpleDepwaitContext()

        depwait_build.current_source_publication.requestDeletion(
            depwait_build.sourcepackagerelease.creator)
        contrib = getUtility(IComponentSet).new('contrib')
        depwait_build.sourcepackagerelease.component = contrib

        depwait_build.updateDependencies()
        self.assertEquals(depwait_build.dependencies, '')


class TestBuildSetMethodsBase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestBuildSetMethodsBase, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create three builds for the publisher's default
        # distroseries.
        self.builds = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.builds += gedit_src_hist.createMissingBuilds()

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED)
        self.builds += firefox_src_hist.createMissingBuilds()

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            status=PackagePublishingStatus.PUBLISHED)
        self.builds += gtg_src_hist.createMissingBuilds()

        # Short-cuts for our tests.
        self.build_set = getUtility(IBuildSet)


class TestBuildSetGetBuildsForArchive(TestBuildSetMethodsBase):

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestBuildSetGetBuildsForArchive, self).setUp()
        self.archive = self.publisher.distroseries.main_archive

    def testGetBuildsForArchiveNoParams(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForArchive(self.archive)
        num_results = builds.count()
        self.assertEquals(3, num_results, "Expected 3 builds but "
                                          "got %s" % num_results)

    def testGetBuildsForArchiveByArchTag(self):
        # Results can be filtered by architecture tag.
        self.builds[0].distroarchseries = self.publisher.distroseries['hppa']
        builds = self.build_set.getBuildsForArchive(self.archive,
                                                    arch_tag="i386")
        num_results = builds.count()
        self.assertEquals(2, num_results, "Expected 2 builds but "
                                          "got %s" % num_results)


class TestBuildSetGetBuildsForBuilder(TestBuildSetMethodsBase):

    def setUp(self):
        super(TestBuildSetGetBuildsForBuilder, self).setUp()

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

    def testGetBuildsForBuilderNoParams(self):
        # All builds should be returned when called without filtering
        builds = self.build_set.getBuildsForBuilder(self.builder.id)
        num_results = builds.count()
        self.assertEquals(3, num_results, "Expected 3 builds but "
                                          "got %s" % num_results)

    def testGetBuildsForBuilderByArchTag(self):
        # Results can be filtered by architecture tag.
        self.builds[0].distroarchseries = self.publisher.distroseries['hppa']
        builds = self.build_set.getBuildsForBuilder(self.builder.id,
                                                    arch_tag="i386")
        num_results = builds.count()
        self.assertEquals(2, num_results, "Expected 2 builds but "
                                          "got %s" % num_results)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
