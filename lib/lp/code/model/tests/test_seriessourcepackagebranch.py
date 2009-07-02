# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Model tests for distro series source package branch links."""

__metaclass__ = type

import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.model.seriessourcepackagebranch import (
    SeriesSourcePackageBranchSet)
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


class TestSeriesSourcePackageBranchSet(TestCaseWithFactory):
    """Tests for `SeriesSourcePackageBranchSet`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.link_set = SeriesSourcePackageBranchSet()
        self.distro = self.factory.makeDistribution()

    def makeLinkedPackageBranch(self, distribution, sourcepackagename):
        """Make a new package branch and make it official."""
        distro_series = self.factory.makeDistroRelease(distribution)
        source_package = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=distro_series)
        branch = self.factory.makePackageBranch(sourcepackage=source_package)
        pocket = PackagePublishingPocket.RELEASE
        # It is possible for the param to be None, so reset to the factory
        # generated one.
        sourcepackagename = source_package.sourcepackagename
        self.link_set.new(
            distro_series, pocket, sourcepackagename, branch, branch.owner)
        return branch

    def test_findForDistributionSourcePackage(self):
        # Make sure that the find method finds official links for all distro
        # series for the distribution source package.
        distro_source_package = self.factory.makeDistributionSourcePackage()
        distribution = distro_source_package.distribution
        sourcepackagename = distro_source_package.sourcepackagename
        # Make two package branches in different series of the same distro.
        b1 = self.makeLinkedPackageBranch(distribution, sourcepackagename)
        b2 = self.makeLinkedPackageBranch(distribution, sourcepackagename)
        # Make one more on same source package on different distro.
        b3 = self.makeLinkedPackageBranch(None, sourcepackagename)
        # Make one more on different source package, same different distro.
        b4 = self.makeLinkedPackageBranch(distribution, None)
        # And one more unrelated linked package branch.
        b5 = self.makeLinkedPackageBranch(None, None)

        links = self.link_set.findForDistributionSourcePackage(
            distro_source_package)
        self.assertEqual(
            sorted([b1, b2]), sorted([link.branch for link in links]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

