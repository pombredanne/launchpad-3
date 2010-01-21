# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BinaryPackageBuildBehavior functionality."""

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadZopelessLayer
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.interfaces.builder import CorruptBuildID
from lp.soyuz.tests.test_build import BaseTestCaseWithThreeBuilds


class BaseTestVerifySlaveBuildID:

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(BaseTestVerifySlaveBuildID, self).setUp()
        self.build = self.builds[0]
        self.other_build = self.builds[1]
        self.builder = self.factory.makeBuilder(name='builder')

    def test_consistent_build_id(self):
        # verifySlaveBuildID returns None if the build and buildqueue
        # ID pair reported by the slave are associated in the database.
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        behavior.verifySlaveBuildID(
            '%d-%d' % (self.build.id, self.build.buildqueue_record.id))

    def test_mismatched_build_id(self):
        # verifySlaveBuildID returns an error if the build and
        # buildqueue exist, but are not associated in the database.
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertRaises(
            CorruptBuildID, behavior.verifySlaveBuildID,
            '%d-%d' % (self.other_build.id, self.build.buildqueue_record.id))

    def test_build_id_without_separator(self):
        # verifySlaveBuildID returns an error if the build ID does not
        # contain a build and build queue ID separated by a hyphen.
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertRaises(
            CorruptBuildID, behavior.verifySlaveBuildID, 'foo')

    def test_build_id_with_missing_build(self):
        # verifySlaveBuildID returns an error if either the build or
        # build queue specified do not exist.
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertRaises(
            CorruptBuildID, behavior.verifySlaveBuildID, '98-99')


class TestVerifySlaveBuildID(BaseTestVerifySlaveBuildID,
                             BaseTestCaseWithThreeBuilds):
    pass

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
