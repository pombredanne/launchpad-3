# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch collections."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchcollection import (
    GenericBranchCollection)
from canonical.launchpad.database.product import Product
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.branch import (
    BranchLifecycleStatus, BranchType)
from canonical.launchpad.interfaces.branchcollection import (
    IAllBranches, IBranchCollection)
from canonical.launchpad.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel)
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestGenericBranchCollection(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

    def test_provides_branchcollection(self):
        # `GenericBranchCollection` provides the `IBranchCollection`
        # interface.
        self.assertProvides(
            GenericBranchCollection(self.store), IBranchCollection)

    def test_getBranches_no_filter_no_branches(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad. By default, there are no branches.
        collection = GenericBranchCollection(self.store)
        self.assertEqual([], list(collection.getBranches()))

    def test_getBranches_no_filter(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad.
        collection = GenericBranchCollection(self.store)
        branch = self.factory.makeAnyBranch()
        self.assertEqual([branch], list(collection.getBranches()))

    def test_getBranches_product_filter(self):
        # If the specified filter is for the branches of a particular product,
        # then the collection contains only branches of that product.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = GenericBranchCollection(
            self.store, [Branch.product == branch.product])
        self.assertEqual([branch], list(collection.getBranches()))

    def test_count(self):
        # The 'count' property of a collection is the number of elements in
        # the collection.
        collection = GenericBranchCollection(self.store)
        self.assertEqual(0, collection.count())
        for i in range(3):
            self.factory.makeAnyBranch()
        self.assertEqual(3, collection.count())

    def test_count_respects_filter(self):
        # If a collection is a subset of all possible branches, then the count
        # will be the size of that subset. That is, 'count' respects any
        # filters that are applied.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = GenericBranchCollection(
            self.store, [Branch.product == branch.product])
        self.assertEqual(1, collection.count())


class TestBranchCollectionFilters(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.all_branches = getUtility(IAllBranches)

    def test_order_by_product_name(self):
        # The result of getBranches() can be ordered by `Product.name`, no
        # matter what filters are applied.
        aardvark = self.factory.makeProduct(name='aardvark')
        badger = self.factory.makeProduct(name='badger')
        branch_a = self.factory.makeProductBranch(product=aardvark)
        branch_b = self.factory.makeProductBranch(product=badger)
        branch_c = self.factory.makePersonalBranch()
        self.assertEqual(
            [branch_a, branch_b, branch_c],
            list(self.all_branches.getBranches().order_by(Product.name)))

    def test_count_respects_visibleByUser_filter(self):
        # IBranchCollection.count() returns the number of branches that
        # getBranches() yields, even when the visibleByUser filter is applied.
        branch = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch(private=True)
        collection = self.all_branches.visibleByUser(branch.owner)
        self.assertEqual(1, collection.getBranches().count())
        self.assertEqual(1, len(list(collection.getBranches())))
        self.assertEqual(1, collection.count())

    def test_ownedBy(self):
        # 'ownedBy' returns a new collection restricted to branches owned by
        # the given person.
        branch = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = self.all_branches.ownedBy(branch.owner)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_in_product(self):
        # 'inProduct' returns a new collection restricted to branches in the
        # given product.
        #
        # NOTE: JonathanLange 2009-02-11: Maybe this should be a more generic
        # method called 'onTarget' that takes a person (for junk), package or
        # product.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeProductBranch()
        branch3 = self.factory.makeAnyBranch()
        collection = self.all_branches.inProduct(branch.product)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_inProject(self):
        # 'inProject' returns a new collection restricted to branches in the
        # given project.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeProductBranch()
        branch3 = self.factory.makeAnyBranch()
        project = self.factory.makeProject()
        removeSecurityProxy(branch.product).project = project
        collection = self.all_branches.inProject(project)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_ownedBy_and_inProduct(self):
        # 'ownedBy' and 'inProduct' can combine to form a collection that is
        # restricted to branches of a particular product owned by a particular
        # person.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(product=product, owner=person)
        branch2 = self.factory.makeAnyBranch(owner=person)
        branch3 = self.factory.makeProductBranch(product=product)
        collection = self.all_branches.inProduct(product).ownedBy(person)
        self.assertEqual([branch], list(collection.getBranches()))
        collection = self.all_branches.ownedBy(person).inProduct(product)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_in_source_package(self):
        # 'inSourcePackage' returns a new collection that only has branches in
        # the given source package.
        branch = self.factory.makePackageBranch()
        branch2 = self.factory.makePackageBranch()
        branch3 = self.factory.makeAnyBranch()
        collection = self.all_branches.inSourcePackage(branch.sourcepackage)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_withLifecycleStatus(self):
        # 'withLifecycleStatus' returns a new collection that only has
        # branches with the given lifecycle statuses.
        branch1 = self.factory.makeAnyBranch(
            lifecycle_status=BranchLifecycleStatus.DEVELOPMENT)
        branch2 = self.factory.makeAnyBranch(
            lifecycle_status=BranchLifecycleStatus.ABANDONED)
        branch3 = self.factory.makeAnyBranch(
            lifecycle_status=BranchLifecycleStatus.MATURE)
        branch4 = self.factory.makeAnyBranch(
            lifecycle_status=BranchLifecycleStatus.DEVELOPMENT)
        collection = self.all_branches.withLifecycleStatus(
            BranchLifecycleStatus.DEVELOPMENT,
            BranchLifecycleStatus.MATURE)
        self.assertEqual(
            set([branch1, branch3, branch4]), set(collection.getBranches()))

    def test_registeredBy(self):
        # 'registeredBy' returns a new collection that only has branches that
        # were registered by the given user.
        registrant = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(
            owner=registrant, registrant=registrant)
        removeSecurityProxy(branch).owner = self.factory.makePerson()
        self.factory.makeAnyBranch()
        collection = self.all_branches.registeredBy(registrant)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_subscribedBy(self):
        # 'subscribedBy' returns a new collection that only has branches that
        # the given user is subscribed to.
        branch = self.factory.makeAnyBranch()
        subscriber = self.factory.makePerson()
        branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)
        collection = self.all_branches.subscribedBy(subscriber)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_relatedTo(self):
        # 'relatedTo' returns a collection that has all branches that a user
        # owns, is subscribed to or registered. No other branches are in this
        # collection.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(person)
        owned_branch = self.factory.makeAnyBranch(owner=person)
        # Unsubscribe the owner, to demonstrate that we show owned branches
        # even if they aren't subscribed.
        owned_branch.unsubscribe(person)
        # Subscribe two other people to the owned branch to make sure
        # that the BranchSubscription join is doing it right.
        self.factory.makeBranchSubscription(branch=owned_branch)
        self.factory.makeBranchSubscription(branch=owned_branch)

        registered_branch = self.factory.makeAnyBranch(
            owner=team, registrant=person)
        subscribed_branch = self.factory.makeAnyBranch()
        subscribed_branch.subscribe(
            person, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)
        related_branches = self.all_branches.relatedTo(person)
        self.assertEqual(
            sorted([owned_branch, registered_branch, subscribed_branch]),
            sorted(related_branches.getBranches()))

    def test_withBranchType(self):
        hosted_branch1 = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED)
        hosted_branch2 = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED)
        mirrored_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        imported_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.IMPORTED)
        branches = self.all_branches.withBranchType(
            BranchType.HOSTED, BranchType.MIRRORED)
        self.assertEqual(
            set([hosted_branch1, hosted_branch2, mirrored_branch]),
            set(branches.getBranches()))

    def test_scanned(self):
        scanned_branch = self.factory.makeAnyBranch()
        self.factory.makeRevisionsForBranch(scanned_branch)
        unscanned_branch = self.factory.makeAnyBranch()
        branches = self.all_branches.scanned()
        self.assertEqual([scanned_branch], list(branches.getBranches()))


class TestGenericBranchCollectionVisibleFilter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.public_branch = self.factory.makeAnyBranch()
        self.private_branch1 = self.factory.makeAnyBranch(private=True)
        self.private_branch2 = self.factory.makeAnyBranch(private=True)
        self.all_branches = getUtility(IAllBranches)

    def test_all_branches(self):
        # Without the visibleByUser filter, all branches are in the
        # collection.
        self.assertEqual(
            set([self.public_branch, self.private_branch1,
                 self.private_branch2]),
            set(self.all_branches.getBranches()))

    def test_anonymous_sees_only_public(self):
        # Anonymous users can see only public branches.
        branches = self.all_branches.visibleByUser(None)
        self.assertEqual([self.public_branch], list(branches.getBranches()))

    def test_random_person_sees_only_public(self):
        # Logged in users with no special permissions can see only public
        # branches.
        person = self.factory.makePerson()
        branches = self.all_branches.visibleByUser(person)
        self.assertEqual([self.public_branch], list(branches.getBranches()))

    def test_owner_sees_own_branches(self):
        # Users can always see the branches that they own, as well as public
        # branches.
        owner = removeSecurityProxy(self.private_branch1).owner
        branches = self.all_branches.visibleByUser(owner)
        self.assertEqual(
            set([self.public_branch, self.private_branch1]),
            set(branches.getBranches()))

    def test_owner_member_sees_own_branches(self):
        # Members of teams that own branches can see branches owned by those
        # teams, as well as public branches.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(team_owner)
        private_branch = self.factory.makeAnyBranch(owner=team, private=True)
        branches = self.all_branches.visibleByUser(team_owner)
        self.assertEqual(
            set([self.public_branch, private_branch]),
            set(branches.getBranches()))

    def test_launchpad_services_sees_all(self):
        # The LAUNCHPAD_SERVICES special user sees *everything*.
        branches = self.all_branches.visibleByUser(LAUNCHPAD_SERVICES)
        self.assertEqual(
            set(self.all_branches.getBranches()), set(branches.getBranches()))

    def test_admins_see_all(self):
        # Launchpad administrators see *everything*.
        admin = self.factory.makePerson()
        admin_team = removeSecurityProxy(
            getUtility(ILaunchpadCelebrities).admin)
        admin_team.addMember(admin, admin_team.teamowner)
        branches = self.all_branches.visibleByUser(admin)
        self.assertEqual(
            set(self.all_branches.getBranches()), set(branches.getBranches()))

    def test_bazaar_experts_see_all(self):
        # Members of the bazaar_experts team see *everything*.
        bzr_experts = removeSecurityProxy(
            getUtility(ILaunchpadCelebrities).bazaar_experts)
        expert = self.factory.makePerson()
        bzr_experts.addMember(expert, bzr_experts.teamowner)
        branches = self.all_branches.visibleByUser(expert)
        self.assertEqual(
            set(self.all_branches.getBranches()), set(branches.getBranches()))

    def test_subscribers_can_see_branches(self):
        # A person subscribed to a branch can see it, even if it's private.
        subscriber = self.factory.makePerson()
        removeSecurityProxy(self.private_branch1).subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)
        branches = self.all_branches.visibleByUser(subscriber)
        self.assertEqual(
            set([self.public_branch, self.private_branch1]),
            set(branches.getBranches()))

    def test_subscribed_team_members_can_see_branches(self):
        # A person in a team that is subscribed to a branch can see that
        # branch, even if it's private.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(team_owner)
        private_branch = self.factory.makeAnyBranch(private=True)
        # Subscribe the team.
        removeSecurityProxy(private_branch).subscribe(
            team, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)
        # Members of the team can see the private branch that the team is
        # subscribed to.
        branches = self.all_branches.visibleByUser(team_owner)
        self.assertEqual(
            set([self.public_branch, private_branch]),
            set(branches.getBranches()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
