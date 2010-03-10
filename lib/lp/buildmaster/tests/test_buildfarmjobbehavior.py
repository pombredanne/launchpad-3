# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BuildFarmJobBehaviorBase."""

from unittest import TestCase, TestLoader

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.model.buildfarmjobbehavior import BuildFarmJobBehaviorBase


class FakeBuildFarmJob:
    """Dummy BuildFarmJob."""
    pass


class TestBuildFarmJobBehaviorBase(TestCase):
    """Test very small, basic bits of BuildFarmJobBehaviorBase."""

    def setUp(self):
        self.behavior = BuildFarmJobBehaviorBase(FakeBuildFarmJob())

    def test_extractBuildStatus_baseline(self):
        # extractBuildStatus picks the name of the build status out of a
        # dict describing the slave's status.
        slave_status = {'build_status': 'BuildStatus.BUILDING'}
        self.assertEqual(
            BuildStatus.BUILDING.name,
            self.behavior.extractBuildStatus(slave_status))

    def test_extractBuildStatus_malformed(self):
        # extractBuildStatus errors out when the status string is not
        # of the form it expects.
        slave_status = {'build_status': 'BUILDING'}
        self.assertRaises(
            AssertionError,
            self.behavior.extractBuildStatus, slave_status)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
