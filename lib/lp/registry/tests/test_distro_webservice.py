# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime

import pytz
from launchpadlib.errors import Unauthorized

from zope.security.management import (
    endInteraction,
    newInteraction,
    )

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.model.seriessourcepackagebranch import (
    SeriesSourcePackageBranchSet,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import (
    api_url,
    launchpadlib_for,
    TestCaseWithFactory,
    )


class TestDistribution(TestCaseWithFactory):
    """Test how distributions behave through the web service."""

    layer = DatabaseFunctionalLayer

    def test_write_without_permission_gives_Unauthorized(self):
        distro = self.factory.makeDistribution()
        endInteraction()
        lp = launchpadlib_for("anonymous-access")
        lp_distro = lp.load(api_url(distro))
        lp_distro.active = False
        self.assertRaises(Unauthorized, lp_distro.lp_save)


class TestGetBranchTips(TestCaseWithFactory):
    """Test the getBranchTips method and it's exposure to the web service."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetBranchTips, self).setUp()
        self.distro = self.factory.makeDistribution()
        series_1 = self.series_1 = self.factory.makeDistroRelease(self.distro)
        series_2 = self.series_2 = self.factory.makeDistroRelease(self.distro)
        source_package = self.factory.makeSourcePackage(distroseries=series_1)
        branch = self.factory.makeBranch(sourcepackage=source_package)
        unofficial_branch =  self.factory.makeBranch(sourcepackage=source_package)
        registrant = self.factory.makePerson()
        now = datetime.now(pytz.UTC)
        sourcepackagename = self.factory.makeSourcePackageName()
        SeriesSourcePackageBranchSet.new(
            series_1, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant, now)
        SeriesSourcePackageBranchSet.new(
            series_2, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant, now)
        self.factory.makeRevisionsForBranch(branch)
        self.branch_name = branch.unique_name
        self.unofficial_branch_name = unofficial_branch.unique_name
        self.branch_last_scanned_id = branch.last_scanned_id
        endInteraction()
        self.lp = launchpadlib_for("anonymous-access")
        self.lp_distro = self.lp.distributions[self.distro.name]

    def test_structure(self):
        """The structure of the results is what we expect."""
        # The results should be structured as a list of
        # (location, tip revision ID, [official series, official series, ...])
        item = self.lp_distro.getBranchTips()[0]
        self.assertEqual(item[0], self.branch_name)
        self.assertTrue(item[1], self.branch_last_scanned_id)
        self.assertEqual(
            sorted(item[2]),
            [self.series_1.name, self.series_2.name])

    def test_same_results(self):
        """Calling getBranchTips directly matches calling it via the API."""
        # The web service transmutes tuples into lists, so we have to do the
        # same to the results of directly calling getBranchTips.
        listified = [list(x) for x in self.distro.getBranchTips()]
        self.assertEqual(listified, self.lp_distro.getBranchTips())

    def test_revisions(self):
        """If a branch has revisions then the most recent one is returned."""
        revision = self.lp_distro.getBranchTips()[0][1]
        self.assertNotEqual(None, revision)

    def test_since(self):
        """If "since" is given, return branches with new tips since then."""
        # There is at least one branch with a tip since the year 2000.
        self.assertNotEqual(0, len(self.lp_distro.getBranchTips(
            since=datetime(2000, 1, 1))))
        # There are no branches with a tip since the year 3000.
        self.assertEqual(0, len(self.lp_distro.getBranchTips(
            since=datetime(3000, 1, 1))))

    def test_series(self):
        """The official series are included in the data."""
        actual_series_names = sorted([self.series_1.name, self.series_2.name])
        returned_series_names = sorted(self.lp_distro.getBranchTips()[0][-1])
        self.assertEqual(actual_series_names, returned_series_names)

    def test_unofficial_branch(self):
        """Not all branches are official."""
        # If a branch isn't official, the last skanned ID will be None and the
        # official distro series list will be empty.
        tips = self.lp_distro.getBranchTips()[1]
        self.assertEqual(tips[0], self.unofficial_branch_name)
        self.assertEqual(tips[1], None)
        self.assertEqual(tips[2], [])
