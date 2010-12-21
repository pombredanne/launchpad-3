# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ISeriesSourcePackageBranch."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    login_person,
    logout,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.seriessourcepackagebranch import (
    IFindOfficialBranchLinks,
    IMakeOfficialBranchLinks,
    ISeriesSourcePackageBranch,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


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
        series_set = getUtility(IMakeOfficialBranchLinks)
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
        # IMakeOfficialBranchLinks.new inserts the new object into the
        # database, giving it an ID.
        series_set = getUtility(IMakeOfficialBranchLinks)
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
        # IMakeOfficialBranchLinks.new returns an
        # ISeriesSourcePackageBranch, know what I mean?
        series_set = getUtility(IMakeOfficialBranchLinks)
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        sspb = series_set.new(
            distroseries, PackagePublishingPocket.RELEASE, sourcepackagename,
            branch, registrant)
        self.assertProvides(sspb, ISeriesSourcePackageBranch)

    def test_findForSourcePackage(self):
        # IFindOfficialBranchLinks.findForSourcePackage returns an empty
        # result set if there are no links from that source package.
        series_set = getUtility(IFindOfficialBranchLinks)
        package = self.factory.makeSourcePackage()
        self.assertEqual([], list(series_set.findForSourcePackage(package)))

    def test_findForSourcePackage_non_empty(self):
        # IFindOfficialBranchLinks.findForSourcePackage returns a result
        # set of links from the source package. Each link is an
        # ISeriesSourcePackageBranch.
        make_branch_links = getUtility(IMakeOfficialBranchLinks)
        branch = self.factory.makePackageBranch()
        package = branch.sourcepackage
        make_branch_links.new(
            package.distroseries, PackagePublishingPocket.RELEASE,
            package.sourcepackagename, branch, self.factory.makePerson())
        find_branch_links = getUtility(IFindOfficialBranchLinks)
        [link] = list(find_branch_links.findForSourcePackage(package))
        self.assertEqual(PackagePublishingPocket.RELEASE, link.pocket)
        self.assertEqual(branch, link.branch)
        self.assertEqual(link.distroseries, package.distroseries)
        self.assertEqual(link.sourcepackagename, package.sourcepackagename)

    def test_findForBranch(self):
        # IFindOfficialBranchLinks.findForBranch returns a result set of
        # links from the branch to source packages & pockets. Each link is an
        # ISeriesSourcePackageBranch.
        make_branch_links = getUtility(IMakeOfficialBranchLinks)
        branch = self.factory.makePackageBranch()
        package = branch.sourcepackage
        make_branch_links.new(
            package.distroseries, PackagePublishingPocket.RELEASE,
            package.sourcepackagename, branch, self.factory.makePerson())
        find_branch_links = getUtility(IFindOfficialBranchLinks)
        [link] = list(find_branch_links.findForBranch(branch))
        self.assertEqual(PackagePublishingPocket.RELEASE, link.pocket)
        self.assertEqual(branch, link.branch)
        self.assertEqual(link.distroseries, package.distroseries)
        self.assertEqual(link.sourcepackagename, package.sourcepackagename)

    def test_delete(self):
        # `delete` ensures that there is no branch associated with that
        # sourcepackage and pocket.
        make_branch_links = getUtility(IMakeOfficialBranchLinks)
        branch = self.factory.makePackageBranch()
        package = branch.sourcepackage
        make_branch_links.new(
            package.distroseries, PackagePublishingPocket.RELEASE,
            package.sourcepackagename, branch, self.factory.makePerson())
        make_branch_links.delete(package, PackagePublishingPocket.RELEASE)
        find_branch_links = getUtility(IFindOfficialBranchLinks)
        self.assertEqual(
            [], list(find_branch_links.findForSourcePackage(package)))

    def test_cannot_edit_branch_link(self):
        # You can only edit an ISeriesSourcePackageBranch if you have edit
        # permissions, which almost no one has.
        series_set = getUtility(IMakeOfficialBranchLinks)
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

