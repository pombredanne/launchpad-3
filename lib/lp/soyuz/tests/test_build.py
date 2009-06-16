# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test Build features."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
