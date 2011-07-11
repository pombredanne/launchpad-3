# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime

import pytz
from launchpadlib.errors import Unauthorized

from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

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

    def test_attempt_to_write_data_without_permission_gives_Unauthorized(self):
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
        self.branch = self.factory.makeBranch(sourcepackage=source_package)
        registrant = self.factory.makePerson()
        now = datetime.now(pytz.UTC)
        sourcepackagename_1 = self.factory.makeSourcePackageName()
        sourcepackagename_2 = self.factory.makeSourcePackageName()
        sspb_1 = SeriesSourcePackageBranchSet.new(
            series_1, PackagePublishingPocket.RELEASE, sourcepackagename_1,
            self.branch, registrant, now)
        sspb_2 = SeriesSourcePackageBranchSet.new(
            series_2, PackagePublishingPocket.RELEASE, sourcepackagename_1,
            self.branch, registrant, now)

        self.factory.makeRevisionsForBranch(self.branch)
        endInteraction()
        self.lp = launchpadlib_for("anonymous-access")
        self.lp_distro = [d for d in self.lp.distributions
            if d.name == self.distro.name][0]

    def test_structure(self):
        """The structure of the results is what we expect."""
        # The results should be structured as a list of
        # (location, tip revision ID, [official series, official series, ...])
        item = self.lp_distro.getBranchTips()[0]
        self.assertTrue(item[0].startswith('~person-name-'))
        self.assertTrue(item[1].startswith('revision-id-'))
        self.assertEqual(sorted(item[2]), [14, 15])

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
        series_ids = sorted([self.series_1.id, self.series_2.id])
        returned_series_ids = sorted(self.lp_distro.getBranchTips()[0][-1])
        self.assertEqual(series_ids, returned_series_ids)
