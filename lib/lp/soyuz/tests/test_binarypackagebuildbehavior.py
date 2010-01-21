# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BinaryPackageBuildBehavior functionality."""

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadZopelessLayer
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.soyuz.tests.test_build import BaseTestCaseWithThreeBuilds


class BaseTestVerifySlaveBuildID:

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(BaseTestVerifySlaveBuildID, self).setUp()
        self.build = self.builds[0]
        self.other_build = self.builds[1]
        self.builder = self.factory.makeBuilder(name='builder')

    def test_consistent_build_id(self):
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertEqual(
            None,
            behavior.verifySlaveBuildID(
                '%d-%d' % (self.build.id, self.build.buildqueue_record.id)))

    def test_mismatched_build_id(self):
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertEqual(
            'Job build entry mismatch',
            behavior.verifySlaveBuildID(
                '%d-%d' % (
                    self.other_build.id, self.build.buildqueue_record.id)))

    def test_build_id_without_separator(self):
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertEqual(
            'Malformed build ID', behavior.verifySlaveBuildID('foo'))

    def test_build_id_with_missing_build(self):
        buildfarmjob = self.build.buildqueue_record.specific_job
        behavior = IBuildFarmJobBehavior(buildfarmjob)
        self.assertEqual(
            'Object not found', behavior.verifySlaveBuildID('98-99'))


class TestVerifySlaveBuildID(BaseTestVerifySlaveBuildID,
                             BaseTestCaseWithThreeBuilds):
    pass

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
