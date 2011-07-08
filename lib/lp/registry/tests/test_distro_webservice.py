# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import datetime

from launchpadlib.errors import Unauthorized

from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
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
        series = self.factory.makeDistroRelease(self.distro)
        source_package = self.factory.makeSourcePackage(distroseries=series)
        self.branch_1 = self.factory.makeBranch(sourcepackage=source_package)
        self.branch_2 = self.factory.makeBranch(sourcepackage=source_package)
        self.factory.makeRevisionsForBranch(self.branch_1)
        self.factory.makeRevisionsForBranch(self.branch_2)
        endInteraction()
        self.lp = launchpadlib_for("anonymous-access")
        self.lp_distro = [d for d in self.lp.distributions
            if d.name == self.distro.name][0]

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
        self.assertNotEqual(0, len(self.lp_distro.getBranchTips(
            since=datetime.datetime(2000, 1, 1))))
        self.assertEqual(0, len(self.lp_distro.getBranchTips(
            since=datetime.datetime(3000, 1, 1))))
