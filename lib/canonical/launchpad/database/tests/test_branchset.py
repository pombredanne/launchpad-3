# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for BranchSet."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, BranchCreatorNotMemberOfOwnerTeam, IProductSet,
    IPersonSet)
from canonical.lp.dbschema import (
    BranchVisibilityPolicy, PersonCreationRationale, TeamSubscriptionPolicy)
from canonical.testing import LaunchpadFunctionalLayer

from zope.component import getUtility


class BranchVisibilityPolicyTestCase(TestCase):
    """Base class for tests to make testing easier."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        # Our test product.
        person_set = getUtility(IPersonSet)

        self.firefox = getUtility(IProductSet).getByName('firefox')
        # Test people
        self.albert, ignored  = person_set.createPersonAndEmail(
            'albert@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='albert', displayname='Albert Tester')
        self.bob, ignored  = person_set.createPersonAndEmail(
            'bob@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='bob', displayname='Bob Tester')
        self.charlie, ignored  = person_set.createPersonAndEmail(
            'charlie@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='charlie', displayname='Charlie Tester')
        self.doug, ignored  = person_set.createPersonAndEmail(
            'doug@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='doug', displayname='Doug Tester')

        self.people = (self.albert, self.bob, self.charlie, self.doug)

        # Test teams.
        self.xray = person_set.newTeam(
            self.albert, 'xray', 'X-Ray Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.yankie = person_set.newTeam(
            self.albert, 'yankie', 'Yankie Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.zulu = person_set.newTeam(
            self.albert, 'zulu', 'Zulu Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.teams = (self.xray, self.yankie, self.zulu)

        # Set the memberships
        self.albert.join(self.xray)
        self.albert.join(self.yankie)
        self.albert.join(self.zulu)
        self.bob.join(self.yankie)
        self.charlie.join(self.zulu)

    def definePolicy(self, policies):
        """Shortcut to help define policies."""
        for team, policy in policies:
            self.firefox.setTeamBranchVisibilityPolicy(team, policy)

    def assertVisibilityPolicy(self, creator, owner, private, subscriber):
        create_private, implicit_subscription_team = (
            BranchSet()._checkVisibilityPolicy(
            creator=creator, owner=owner, product=self.firefox))
        self.assertEqual(
            create_private, private,
            "Branch privacy doesn't match. Expected %s, got %s"
            % (private, create_private))
        self.assertEqual(
            implicit_subscription_team, subscriber,
            "Implicit subscriber doesn't match. Expected %s, got %s."
            % (getattr(subscriber, 'name', None),
               getattr(implicit_subscription_team, 'name', None)))

    def assertPublic(self, creator, owner):
        self.assertVisibilityPolicy(creator, owner, False, None)

    def assertPrivateSubscriber(self, creator, owner, subscriber):
        self.assertVisibilityPolicy(creator, owner, True, subscriber)

    def assertBranchCreationForbidden(self, creator, owner):
        self.assertRaises(
            BranchCreationForbidden,
            BranchSet()._checkVisibilityPolicy,
            creator=creator, owner=owner, product=self.firefox)

    def assertBranchCreatorNotMemberOfOwnerTeam(self, creator, owner):
        self.assertRaises(
            BranchCreatorNotMemberOfOwnerTeam,
            BranchSet()._checkVisibilityPolicy,
            creator=creator, owner=owner, product=self.firefox)



class TestTeamMembership(BranchVisibilityPolicyTestCase):
    """Test the sample data team membership."""

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team Xray team.")
        self.failUnless(albert.inTeam(yankie),
                        "Albert should be in the Yankie.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of only Yankie.
        self.failIf(bob.inTeam(xray),
                    "Bob should not be in team Xray team.")
        self.failUnless(bob.inTeam(yankie),
                        "Bob should be in the Yankie team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of only Zulu.
        self.failIf(charlie.inTeam(xray),
                    "Charlie should not be in team Xray team.")
        self.failIf(charlie.inTeam(yankie),
                    "Charlie should not be in the Yankie team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team Xray team.")
        self.failIf(doug.inTeam(yankie),
                    "Doug should not be in the Yankie team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")


class PolicySimple(BranchVisibilityPolicyTestCase):
    """Test the policy where Public for all except one team where private."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_branches(self):
        # Branches created by people not in Xray will be public.
        self.assertPublic(self.charlie, self.charlie)
        self.assertBranchCreatorNotMemberOfOwnerTeam(self.charlie, self.xray)

        # Branches created by people in Xray will be private if in
        # thier own namespace.
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)
        # Private in X-Ray team namespace.
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        # Public in the other namespaces.
        self.assertPublic(self.albert, self.yankie)


class PolicyPrivateOnly(BranchVisibilityPolicyTestCase):
    """Test the policy where PUBLIC for all except one team where PRIVATE_ONLY.

    PRIVATE_ONLY only stops the user from changing the branch to public.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.xray, BranchVisibilityPolicy.PRIVATE_ONLY),
            ))

    def test_branches(self):
        # Branches created by people not in Xray will be public.
        self.assertPublic(self.charlie, self.charlie)
        self.assertBranchCreatorNotMemberOfOwnerTeam(self.charlie, self.xray)

        # Branches created by people in Xray will be private if in
        # thier own namespace.
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)
        # Private in X-Ray team namespace.
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        # Public in the other namespaces.
        self.assertPublic(self.albert, self.yankie)


class PolicyForbidden(BranchVisibilityPolicyTestCase):
    """Test the policy where FORBIDDEN for all, PUBLIC for some and PRIVATE
    for others.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.FORBIDDEN),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.yankie, BranchVisibilityPolicy.PUBLIC),
            ))

    def test_branches(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams

        # Branches created by people not in Xray or Yankie is
        # forbidden.
        self.assertBranchCreationForbidden(charlie, charlie)
        self.assertBranchCreationForbidden(charlie, zulu)
        self.assertBranchCreatorNotMemberOfOwnerTeam(charlie, yankie)
        self.assertBranchCreationForbidden(doug, doug)
        self.assertBranchCreatorNotMemberOfOwnerTeam(doug, yankie)

        # Branches created by people in the Yankie will be public.
        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankie)

        # Since Albert is a member of all three teams, he can write
        # to all team locations.
        # When Albert creates branches owned by himself, they
        # are subscribed by Xray
        self.assertPrivateSubscriber(albert, albert, xray)
        # Since the owner of the branch is Xray, Xray do
        # not need to be subscribed.
        self.assertPrivateSubscriber(albert, xray, None)
        # Since ubuntu-team can have public branches, when a branch
        # is created by Albert but owned by ubuntu-team, the branches
        # are considered public.
        self.assertPublic(albert, yankie)
        # Branches cannot be created for other teams.
        self.assertBranchCreationForbidden(albert, zulu)


class PolicyTeamOverlap(BranchVisibilityPolicyTestCase):
    """Test the policy where a user is a member of multiple teams."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.zulu, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_branches(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams
        # Bob is only a member of Yankie team, so the default policy
        # (PUBLIC) is used.
        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankie)
        # Doug, who is not a member of any team, creates public branches.
        self.assertPublic(doug, doug)

        # Charlie is only a member of Zulu.
        # Since Charlie is only a member of one team, normal behaviour applies.
        # Zulu will be subscribed to new branches created by Charlie.
        self.assertPrivateSubscriber(charlie, charlie, zulu)
        self.assertPrivateSubscriber(charlie, zulu, None)

        # Albert is in both private teams.
        # Albert is not subscribed when he is the owner.
        self.assertPrivateSubscriber(albert, albert, None)
        # Albert is subscribed when he is not the owner.
        self.assertPrivateSubscriber(albert, zulu, None)
        self.assertPrivateSubscriber(albert, xray, None)
        # When creating a branch for a team that has public branches
        # the branch is public.
        self.assertPublic(albert, yankie)


class PolicyTeamAll(BranchVisibilityPolicyTestCase):
    """Test the policy where a user is a member of multiple teams."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.FORBIDDEN),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.yankie, BranchVisibilityPolicy.PRIVATE_ONLY),
            (self.zulu, BranchVisibilityPolicy.PUBLIC),
            ))

    def test_branches(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams

        # Doug is not in any teams.
        self.assertBranchCreationForbidden(doug, doug)

        # Bob is only a member of Yankie team, so private branches.
        self.assertPrivateSubscriber(bob, bob, yankie)
        self.assertPrivateSubscriber(bob, yankie, None)

        # Charlie is only a member of Zulu.
        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        # Can't choose which team to subscribe to Albert's
        # branch, so don't subscribe any.
        self.assertPrivateSubscriber(albert, albert, None)
        # Zulu branches are public.
        self.assertPublic(albert, zulu)
        # Branches for Xray and Yankie are private.
        self.assertPrivateSubscriber(albert, xray, None)
        self.assertPrivateSubscriber(albert, yankie, None)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
