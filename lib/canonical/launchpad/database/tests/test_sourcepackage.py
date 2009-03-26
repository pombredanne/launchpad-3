# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Unit tests for ISourcePackage implementations."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person, logout
from canonical.launchpad.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.interfaces.seriessourcepackagebranch import (
    ISeriesSourcePackageBranchSet)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class TestSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        person = self.factory.makePerson()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        removeSecurityProxy(ubuntu_branches).addMember(
            person, ubuntu_branches.teamowner)
        login_person(person)
        self.addCleanup(logout)

    def test_path(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual(
            '%s/%s/%s' % (
                sourcepackage.distribution.name,
                sourcepackage.distroseries.name,
                sourcepackage.sourcepackagename.name),
            sourcepackage.path)

    def test_getBranch_no_branch(self):
        # If there's no official branch for that pocket of a source package,
        # getBranch returns None.
        sourcepackage = self.factory.makeSourcePackage()
        branch = sourcepackage.getBranch(PackagePublishingPocket.RELEASE)
        self.assertIs(None, branch)

    def test_getBranch_exists(self):
        # If there is a SeriesSourcePackageBranch entry for that source
        # package and pocket, then return the branch.
        sourcepackage = self.factory.makeSourcePackage()
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        getUtility(ISeriesSourcePackageBranchSet).new(
            sourcepackage.distroseries, PackagePublishingPocket.RELEASE,
            sourcepackage.sourcepackagename, branch, registrant)
        official_branch = sourcepackage.getBranch(
            PackagePublishingPocket.RELEASE)
        self.assertEqual(branch, official_branch)

    def test_setBranch(self):
        # We can set the official branch for a pocket of a source package.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        self.assertEqual(branch, sourcepackage.getBranch(pocket))

    def test_development_version(self):
        # ISourcePackage.development_version gets the development version of
        # the source package.
        distribution = self.factory.makeDistribution()
        dev_series = self.factory.makeDistroRelease(
            distribution=distribution, status=DistroSeriesStatus.DEVELOPMENT)
        other_series = self.factory.makeDistroRelease(
            distribution=distribution, status=DistroSeriesStatus.OBSOLETE)
        self.assertEqual(dev_series, distribution.currentseries)
        dev_sourcepackage = self.factory.makeSourcePackage(
            distroseries=dev_series)
        other_sourcepackage = self.factory.makeSourcePackage(
            distroseries=other_series,
            sourcepackagename=dev_sourcepackage.sourcepackagename)
        self.assertEqual(
            dev_sourcepackage, other_sourcepackage.development_version)
        self.assertEqual(
            dev_sourcepackage, dev_sourcepackage.development_version)


class TestSourcePackageSecurity(TestCaseWithFactory):
    """Tests for source package branch linking security."""

    layer = DatabaseFunctionalLayer

    def test_cannot_setBranch(self):
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        self.assertRaises(
            Unauthorized, sourcepackage.setBranch, pocket, branch, registrant)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
