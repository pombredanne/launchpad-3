# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Tests for ISeriesSourcePackageBranch."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz

import transaction

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import ANONYMOUS, login, login_person, logout
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.interfaces.seriessourcepackagebranch import (
    ISeriesSourcePackageBranch, ISeriesSourcePackageBranchSet)
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestSeriesSourcePackageBranch(TestCaseWithFactory):
    """Tests for `ISeriesSourcePackageBranch`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        person = self.factory.makePerson()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        removeSecurityProxy(ubuntu_branches).addMember(
            person, ubuntu_branches.teamowner)
        login_person(person)
        self.addCleanup(logout)

    def test_new_sets_attributes(self):
        # ISeriesSourcePackageBranchSet.new sets all the defined attributes on
        # the interface.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        now = datetime.now(pytz.UTC)
        sspb = series_set.new(
            distroseries, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant, now)
        self.assertEqual(distroseries, sspb.distroseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, sspb.pocket)
        self.assertEqual(sourcepackagename, sspb.sourcepackagename)
        self.assertEqual(branch, sspb.branch)
        self.assertEqual(registrant, sspb.registrant)
        self.assertEqual(now, sspb.date_created)

    def test_new_inserts_into_db(self):
        # ISeriesSourcePackageBranchSet.new inserts the new object into the
        # database, giving it an ID.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        sspb = series_set.new(
            distroseries, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant)
        transaction.commit()
        self.assertIsNot(sspb.id, None)

    def test_new_returns_ISeriesSourcePackageBranch(self):
        # ISeriesSourcePackageBranchSet.new returns an
        # ISeriesSourcePackageBranch, know what I mean?
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        sspb = series_set.new(
            distroseries, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant)
        self.assertProvides(sspb, ISeriesSourcePackageBranch)

    def test_findForSourcePackage(self):
        # ISeriesSourcePackageBranchSet.findForSourcePackage returns an empty
        # result set if there are no links from that source package.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        package = self.factory.makeSourcePackage()
        self.assertEqual([], list(series_set.findForSourcePackage(package)))

    def test_findForSourcePackage_non_empty(self):
        # ISeriesSourcePackageBranchSet.findForSourcePackage returns a list of
        # links from the source package. Each link is an
        # ISeriesSourcePackageBranch.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        branch = self.factory.makePackageBranch()
        package = branch.sourcepackage
        series_set.new(
            package.distroseries, PackagePublishingPocket.RELEASE,
            package.sourcepackagename, branch, self.factory.makePerson())
        [link] = list(series_set.findForSourcePackage(package))
        self.assertEqual(PackagePublishingPocket.RELEASE, link.pocket)
        self.assertEqual(branch, link.branch)
        self.assertEqual(link.distroseries, package.distroseries)
        self.assertEqual(link.sourcepackagename, package.sourcepackagename)

    def test_delete(self):
        # `delete` ensures that there is no branch associated with that
        # sourcepackage and pocket.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        branch = self.factory.makePackageBranch()
        package = branch.sourcepackage
        series_set.new(
            package.distroseries, PackagePublishingPocket.RELEASE,
            package.sourcepackagename, branch, self.factory.makePerson())
        series_set.delete(package, PackagePublishingPocket.RELEASE)
        self.assertEqual([], list(series_set.findForSourcePackage(package)))

    def test_cannot_edit_branch_link(self):
        # You can only edit an ISeriesSourcePackageBranch if you have edit
        # permissions, which almost no one has.
        series_set = getUtility(ISeriesSourcePackageBranchSet)
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        sspb = series_set.new(
            distroseries, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant)
        logout()
        login(ANONYMOUS)
        self.assertRaises(
            Unauthorized, setattr, sspb, 'pocket',
            PackagePublishingPocket.BACKPORTS)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

