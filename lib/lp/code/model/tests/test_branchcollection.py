# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch collections."""

__metaclass__ = type

from datetime import datetime
import unittest

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.enums import (
    BranchLifecycleStatus, BranchMergeProposalStatus,
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    BranchType, CodeReviewNotificationLevel)
from lp.code.model.branch import Branch
from lp.code.model.branchcollection import (
    GenericBranchCollection)
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.interfaces.branchcollection import (
    IAllBranches, IBranchCollection)
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from lp.testing import TestCaseWithFactory
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
            list(self.all_branches.getBranches()
                 .order_by(Branch.target_suffix)))

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

    def test_modifiedSince(self):
        # Only branches modified since the time specified will be returned.
        old_branch = self.factory.makeAnyBranch()
        old_branch.date_last_modified = datetime(2008, 1, 1, tzinfo=pytz.UTC)
        new_branch = self.factory.makeAnyBranch()
        new_branch.date_last_modified = datetime(2009, 1, 1, tzinfo=pytz.UTC)
        branches = self.all_branches.modifiedSince(
            datetime(2008, 6, 1, tzinfo=pytz.UTC))
        self.assertEqual([new_branch], list(branches.getBranches()))

    def test_scannedSince(self):
        # Only branches scanned since the time specified will be returned.
        old_branch = self.factory.makeAnyBranch()
        removeSecurityProxy(old_branch).last_scanned = (
            datetime(2008, 1, 1, tzinfo=pytz.UTC))
        new_branch = self.factory.makeAnyBranch()
        removeSecurityProxy(new_branch).last_scanned = (
            datetime(2009, 1, 1, tzinfo=pytz.UTC))
        branches = self.all_branches.scannedSince(
            datetime(2008, 6, 1, tzinfo=pytz.UTC))
        self.assertEqual([new_branch], list(branches.getBranches()))

    def test_targetedBy(self):
        # Only branches that are merge targets are returned.
        target_branch = self.factory.makeProductBranch()
        registrant = self.factory.makePerson()
        self.factory.makeBranchMergeProposal(
            target_branch=target_branch, registrant=registrant)
        # And another not registered by registrant.
        self.factory.makeBranchMergeProposal()
        branches = self.all_branches.targetedBy(registrant)
        self.assertEqual([target_branch], list(branches.getBranches()))


class TestGenericBranchCollectionVisibleFilter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.public_branch = self.factory.makeAnyBranch(name='public')
        self.private_branch1 = self.factory.makeAnyBranch(
            private=True, name='private1')
        self.private_branch2 = self.factory.makeAnyBranch(
            private=True, name='private2')
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

    def test_visibility_then_product(self):
        # We can apply other filters after applying the visibleByUser filter.
        second_public_branch = self.factory.makeAnyBranch()
        branches = self.all_branches.visibleByUser(None).inProduct(
            self.public_branch.product).getBranches()
        self.assertEqual([self.public_branch], list(branches))

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
        private_branch = self.factory.makeAnyBranch(
            owner=team, private=True, name='team')
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


class TestBranchMergeProposals(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.all_branches = getUtility(IAllBranches)

    def test_empty_branch_merge_proposals(self):
        proposals = self.all_branches.getMergeProposals()
        self.assertEqual([], list(proposals))

    def test_some_branch_merge_proposals(self):
        mp = self.factory.makeBranchMergeProposal()
        proposals = self.all_branches.getMergeProposals()
        self.assertEqual([mp], list(proposals))

    def test_just_owned_branch_merge_proposals(self):
        # If the collection only includes branches owned by a person, the
        # getMergeProposals() will only return merge proposals for branches
        # that are owned by that person.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        branch1 = self.factory.makeProductBranch(
            product=product, owner=person)
        branch2 = self.factory.makeProductBranch(
            product=product, owner=person)
        branch3 = self.factory.makeProductBranch(product=product)
        branch4 = self.factory.makeProductBranch(product=product)
        target = self.factory.makeProductBranch(product=product)
        mp1 = self.factory.makeBranchMergeProposal(
            target_branch=target, source_branch=branch1)
        mp2 = self.factory.makeBranchMergeProposal(
            target_branch=target, source_branch=branch2)
        mp3 = self.factory.makeBranchMergeProposal(
            target_branch=target, source_branch=branch3)
        collection = self.all_branches.ownedBy(person)
        proposals = collection.getMergeProposals()
        self.assertEqual(set([mp1, mp2]), set(proposals))

    def test_merge_proposals_in_product(self):
        mp1 = self.factory.makeBranchMergeProposal()
        mp2 = self.factory.makeBranchMergeProposal()
        product = mp1.source_branch.product
        collection = self.all_branches.inProduct(product)
        proposals = collection.getMergeProposals()
        self.assertEqual([mp1], list(proposals))

    def test_target_branch_private(self):
        # The target branch must be in the branch collection, as must the
        # source branch.
        mp1 = self.factory.makeBranchMergeProposal()
        removeSecurityProxy(mp1.target_branch).private = True
        collection = self.all_branches.visibleByUser(None)
        proposals = collection.getMergeProposals()
        self.assertEqual([], list(proposals))

    def test_status_restriction(self):
        mp1 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.WORK_IN_PROGRESS)
        mp2 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        mp3 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.CODE_APPROVED)
        proposals = self.all_branches.getMergeProposals(
            [BranchMergeProposalStatus.WORK_IN_PROGRESS,
             BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual(set([mp1, mp2]), set(proposals))

    def test_status_restriction_with_product_filter(self):
        # getMergeProposals returns the merge proposals with a particular
        # status that are _inside_ the branch collection. mp1 is in the
        # product with NEEDS_REVIEW, mp2 is outside of the product and mp3 has
        # an excluded status.
        mp1 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        mp2 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        product = mp1.source_branch.product
        branch1 = self.factory.makeProductBranch(product=product)
        branch2 = self.factory.makeProductBranch(product=product)
        mp3 = self.factory.makeBranchMergeProposal(
            target_branch=branch1, source_branch=branch2,
            set_state=BranchMergeProposalStatus.CODE_APPROVED)
        collection = self.all_branches.inProduct(product)
        proposals = collection.getMergeProposals(
            [BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual([mp1], list(proposals))


class TestBranchMergeProposalsForReviewer(TestCaseWithFactory):
    """Tests for IBranchCollection.getProposalsForReviewer()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use the admin user as we don't care about who can and can't call
        # nominate reviewer in this test.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        remove_all_sample_data_branches()
        self.all_branches = getUtility(IAllBranches)

    def test_getProposalsForReviewer(self):
        reviewer = self.factory.makePerson()
        proposal = self.factory.makeBranchMergeProposal()
        proposal.nominateReviewer(reviewer, reviewer)
        proposal2 = self.factory.makeBranchMergeProposal()
        proposals = self.all_branches.getMergeProposalsForReviewer(reviewer)
        self.assertEqual([proposal], list(proposals))

    def test_getProposalsForReviewer_filter_status(self):
        reviewer = self.factory.makePerson()
        proposal1 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        proposal1.nominateReviewer(reviewer, reviewer)
        proposal2 = self.factory.makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.WORK_IN_PROGRESS)
        proposal2.nominateReviewer(reviewer, reviewer)
        proposals = self.all_branches.getMergeProposalsForReviewer(
            reviewer, [BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual([proposal1], list(proposals))

    def test_getProposalsForReviewer_anonymous(self):
        # Don't include proposals if the target branch is private for
        # anonymous views.
        reviewer = self.factory.makePerson()
        target_branch = self.factory.makeAnyBranch(private=True)
        proposal = self.factory.makeBranchMergeProposal(
            target_branch=target_branch)
        proposal.nominateReviewer(reviewer, reviewer)
        proposals = self.all_branches.visibleByUser(
            None).getMergeProposalsForReviewer(reviewer)
        self.assertEqual([], list(proposals))

    def test_getProposalsForReviewer_anonymous_source_private(self):
        # Don't include proposals if the source branch is private for
        # anonymous views.
        reviewer = self.factory.makePerson()
        product = self.factory.makeProduct()
        source_branch = self.factory.makeProductBranch(
            product=product, private=True)
        target_branch = self.factory.makeProductBranch(product=product)
        proposal = self.factory.makeBranchMergeProposal(
            source_branch=source_branch, target_branch=target_branch)
        proposal.nominateReviewer(reviewer, reviewer)
        proposals = self.all_branches.visibleByUser(
            None).getMergeProposalsForReviewer(reviewer)
        self.assertEqual([], list(proposals))

    def test_getProposalsForReviewer_for_product(self):
        reviewer = self.factory.makePerson()
        proposal = self.factory.makeBranchMergeProposal()
        proposal.nominateReviewer(reviewer, reviewer)
        proposal2 = self.factory.makeBranchMergeProposal()
        proposal2.nominateReviewer(reviewer, reviewer)
        proposals = self.all_branches.inProduct(
            proposal.source_branch.product).getMergeProposalsForReviewer(
            reviewer)
        self.assertEqual([proposal], list(proposals))


class TestSearch(TestCaseWithFactory):
    """Tests for IBranchCollection.search()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.collection = getUtility(IAllBranches)

    def test_exact_match_unique_name(self):
        # If you search for a unique name of a branch that exists, you'll get
        # a single result with a branch with that branch name.
        branch = self.factory.makeAnyBranch()
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search(branch.unique_name)
        self.assertEqual([branch], list(search_results))

    def test_unique_name_match_not_in_collection(self):
        # If you search for a unique name of a branch that does not exist,
        # you'll get an empty result set.
        branch = self.factory.makeAnyBranch()
        collection = self.collection.inProduct(self.factory.makeProduct())
        search_results = collection.search(branch.unique_name)
        self.assertEqual([], list(search_results))

    def test_exact_match_remote_url(self):
        # If you search for the remote URL of a branch, and there's a branch
        # with that URL, you'll get a single result with a branch with that
        # branch name.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search(branch.url)
        self.assertEqual([branch], list(search_results))

    def test_exact_match_launchpad_url(self):
        # If you search for the Launchpad URL of a branch, and there is a
        # branch with that URL, then you get a single result with that branch.
        branch = self.factory.makeAnyBranch()
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search(branch.codebrowse_url())
        self.assertEqual([branch], list(search_results))

    def test_exact_match_url_trailing_slash(self):
        # Sometimes, users are inconsiderately unaware of our arbitrary
        # database restrictions and will put trailing slashes on their search
        # queries. Rather bravely, we refuse to explode in this case.
        branch = self.factory.makeAnyBranch()
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search(branch.codebrowse_url() + '/')
        self.assertEqual([branch], list(search_results))

    def test_match_exact_branch_name(self):
        # search returns all branches with the same name as the search term.
        branch1 = self.factory.makeAnyBranch(name='foo')
        branch2 = self.factory.makeAnyBranch(name='foo')
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_sub_branch_name(self):
        # search returns all branches which have a name of which the search
        # term is a substring.
        branch1 = self.factory.makeAnyBranch(name='afoo')
        branch2 = self.factory.makeAnyBranch(name='foob')
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_exact_owner_name(self):
        # search returns all branches which have an owner with a name matching
        # the server.
        person = self.factory.makePerson(name='foo')
        branch1 = self.factory.makeAnyBranch(owner=person)
        branch2 = self.factory.makeAnyBranch(owner=person)
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_sub_owner_name(self):
        # search returns all branches that have an owner name where the search
        # term is a substring of the owner name.
        person1 = self.factory.makePerson(name='foom')
        branch1 = self.factory.makeAnyBranch(owner=person1)
        person2 = self.factory.makePerson(name='afoo')
        branch2 = self.factory.makeAnyBranch(owner=person2)
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_exact_product_name(self):
        # search returns all branches that have a product name where the
        # product name is the same as the search term.
        product = self.factory.makeProduct(name='foo')
        branch1 = self.factory.makeAnyBranch(product=product)
        branch2 = self.factory.makeAnyBranch(product=product)
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_sub_product_name(self):
        # search returns all branches that have a product name where the
        # search terms is a substring of the product name.
        product1 = self.factory.makeProduct(name='foom')
        branch1 = self.factory.makeProductBranch(product=product1)
        product2 = self.factory.makeProduct(name='afoo')
        branch2 = self.factory.makeProductBranch(product=product2)
        not_branch = self.factory.makeAnyBranch()
        search_results = self.collection.search('foo')
        self.assertEqual(set([branch1, branch2]), set(search_results))

    def test_match_sub_distro_name(self):
        # search returns all branches that have a distro name where the search
        # term is a substring of the distro name.
        branch = self.factory.makePackageBranch()
        not_branch = self.factory.makeAnyBranch()
        search_term = branch.distribution.name[1:]
        search_results = self.collection.search(search_term)
        self.assertEqual([branch], list(search_results))

    def test_match_sub_distroseries_name(self):
        # search returns all branches that have a distro series with a name
        # that the search term is a substring of.
        branch = self.factory.makePackageBranch()
        not_branch = self.factory.makeAnyBranch()
        search_term = branch.distroseries.name[1:]
        search_results = self.collection.search(search_term)
        self.assertEqual([branch], list(search_results))

    def test_match_sub_sourcepackage_name(self):
        # search returns all branches that have a source package with a name
        # that contains the search term.
        branch = self.factory.makePackageBranch()
        not_branch = self.factory.makeAnyBranch()
        search_term = branch.sourcepackagename.name[1:]
        search_results = self.collection.search(search_term)
        self.assertEqual([branch], list(search_results))

    def test_dont_match_product_if_in_product(self):
        # If the container is restricted to the product, then we don't match
        # the product name.
        product = self.factory.makeProduct('foo')
        branch1 = self.factory.makeProductBranch(product=product, name='foo')
        branch2 = self.factory.makeProductBranch(product=product, name='bar')
        search_results = self.collection.inProduct(product).search('foo')
        self.assertEqual([branch1], list(search_results))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
