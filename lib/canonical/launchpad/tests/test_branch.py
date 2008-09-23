# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of Branch and BranchSet."""

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branch import (
    BranchSet, DEFAULT_BRANCH_LISTING_SORT)
from canonical.launchpad.interfaces import (
    BranchListingSort, BranchSubscriptionNotificationLevel,
    BranchSubscriptionDiffSize, CodeReviewNotificationLevel)
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.security import AccessBranch
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestListingToSortOrder(unittest.TestCase):
    """Tests for the BranchSet._listingSortToOrderBy static method.

    This method translates values from the BranchListingSort enumeration into
    values suitable to pass to orderBy in queries against BranchWithSortKeys.
    """

    def assertColumnNotReferenced(self, column, order_by_list):
        """Ensure that column is not referenced in any way in order_by_list.
        """
        self.failIf(column in order_by_list or
                    ('-' + column) in order_by_list)

    def test_default(self):
        """Test that passing None results in the default list."""
        self.assertEquals(BranchSet._listingSortToOrderBy(None),
                          DEFAULT_BRANCH_LISTING_SORT)

    def test_lifecycle(self):
        """Test with an option that's part of the default sort.

        Sorting on LIFECYCYLE moves the lifecycle reference to the
        first element of the output."""
        # Check that this isn't a no-op.
        self.assertNotEquals(DEFAULT_BRANCH_LISTING_SORT[0],
                             '-lifecycle_status')
        lifecycle_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.LIFECYCLE)
        self.assertEquals(lifecycle_order[0], '-lifecycle_status')
        # Check that no reference to lifecycle remains in the list
        self.assertColumnNotReferenced('lifecycle_status', lifecycle_order[1:])

    def test_sortOnColumNotInDefaultSortOrder(self):
        """Test with an option that's not part of the default sort.

        This should put the passed option first in the list, but leave
        the rest the same.
        """
        self.assertColumnNotReferenced(
            'date_created', DEFAULT_BRANCH_LISTING_SORT)
        registrant_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.OLDEST_FIRST)
        self.assertEquals(registrant_order[0], 'date_created')
        self.assertEquals(registrant_order[1:], DEFAULT_BRANCH_LISTING_SORT)


class TestAccessBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertAuthenticatedAccess(self, branch, person, can_access):
        branch = removeSecurityProxy(branch)
        self.assertEqual(
            can_access, AccessBranch(branch).checkAuthenticated(person))

    def assertUnauthenticatedAccess(self, branch, can_access):
        branch = removeSecurityProxy(branch)
        self.assertEqual(
            can_access, AccessBranch(branch).checkUnauthenticated())

    def test_publicBranchUnauthenticated(self):
        # Public branches can be accessed without authentication.
        branch = self.factory.makeBranch()
        self.assertUnauthenticatedAccess(branch, True)

    def test_publicBranchArbitraryUser(self):
        # Public branches can be accessed by anyone.
        branch = self.factory.makeBranch()
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(branch, person, True)

    def test_privateBranchUnauthenticated(self):
        # Private branches cannot be accessed without authentication.
        branch = self.factory.makeBranch(private=True)
        self.assertUnauthenticatedAccess(branch, False)

    def test_privateBranchOwner(self):
        # The owner of a branch can always access it.
        owner = self.factory.makePerson()
        branch = self.factory.makeBranch(private=True, owner=owner)
        self.assertAuthenticatedAccess(branch, owner, True)

    def test_privateBranchOwnerMember(self):
        # Any member of the team that owns the branch can access it.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(team_owner)
        person = self.factory.makePerson()
        removeSecurityProxy(team).addMember(person, team_owner)
        branch = self.factory.makeBranch(private=True, owner=team)
        self.assertAuthenticatedAccess(branch, person, True)

    def test_privateBranchBazaarExperts(self):
        # The Bazaar experts can access any branch.
        celebs = getUtility(ILaunchpadCelebrities)
        branch = self.factory.makeBranch(private=True)
        self.assertAuthenticatedAccess(branch, celebs.bazaar_experts, True)

    def test_privateBranchAdmins(self):
        # Launchpad admins can access any branch.
        celebs = getUtility(ILaunchpadCelebrities)
        branch = self.factory.makeBranch(private=True)
        self.assertAuthenticatedAccess(branch, celebs.admin, True)

    def test_privateBranchSubscriber(self):
        # If you are subscribed to a branch, you can access it.
        branch = self.factory.makeBranch(private=True)
        person = self.factory.makePerson()
        removeSecurityProxy(branch).subscribe(
            person, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)
        self.assertAuthenticatedAccess(branch, person, True)

    def test_privateBranchAnyoneElse(self):
        # In general, you can't access a private branch.
        branch = self.factory.makeBranch(private=True)
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(branch, person, False)

    def test_stackedOnPrivateBranchUnauthenticated(self):
        # If a branch is stacked on a private branch, then you cannot access
        # it when unauthenticated.
        stacked_on_branch = self.factory.makeBranch(private=True)
        stacked_branch = self.factory.makeBranch(stacked_on=stacked_on_branch)
        self.assertUnauthenticatedAccess(stacked_branch, False)

    def test_stackedOnPrivateBranchAuthenticated(self):
        # If a branch is stacked on a private branch, you can only access it
        # if you can access both branches.
        stacked_on_branch = self.factory.makeBranch(private=True)
        stacked_branch = self.factory.makeBranch(stacked_on=stacked_on_branch)
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(stacked_branch, person, False)

    def test_manyLevelsOfStackingUnauthenticated(self):
        # If a branch is stacked on a branch stacked on a private branch, you
        # still can't access it when unauthenticated.
        stacked_on_branch = self.factory.makeBranch(private=True)
        branch_a = self.factory.makeBranch(stacked_on=stacked_on_branch)
        branch_b = self.factory.makeBranch(stacked_on=branch_a)
        self.assertUnauthenticatedAccess(branch_b, False)

    def test_manyLevelsOfStackingAuthenticated(self):
        # If a branch is stacked on a branch stacked on a private branch, you
        # still can't access it when unauthenticated.
        stacked_on_branch = self.factory.makeBranch(private=True)
        branch_a = self.factory.makeBranch(stacked_on=stacked_on_branch)
        branch_b = self.factory.makeBranch(stacked_on=branch_a)
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(branch_b, person, False)

    def test_loopedPublicStackedOn(self):
        # It's possible, although nonsensical, for branch stackings to form a
        # loop. e.g., branch A is stacked on branch B is stacked on branch A.
        # If all of these branches are public, then we want anyone to be able
        # to access it / them.
        stacked_branch = self.factory.makeBranch()
        removeSecurityProxy(stacked_branch).stacked_on = stacked_branch
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(stacked_branch, person, True)

    def test_loopedPrivateStackedOn(self):
        # It's possible, although nonsensical, for branch stackings to form a
        # loop. e.g., branch A is stacked on branch B is stacked on branch A.
        # If all of these branches are private, then only people who can
        # access all of them can get to them.
        stacked_branch = self.factory.makeBranch(private=True)
        removeSecurityProxy(stacked_branch).stacked_on = stacked_branch
        person = self.factory.makePerson()
        self.assertAuthenticatedAccess(stacked_branch, person, False)

    def test_loopedPublicStackedOnUnauthenticated(self):
        # It's possible, although nonsensical, for branch stackings to form a
        # loop. e.g., branch A is stacked on branch B is stacked on branch A.
        # If all of these branches are public, then you can get them without
        # being logged in.
        stacked_branch = self.factory.makeBranch()
        removeSecurityProxy(stacked_branch).stacked_on = stacked_branch
        self.assertUnauthenticatedAccess(stacked_branch, True)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
