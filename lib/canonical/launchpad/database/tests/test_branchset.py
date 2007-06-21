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
    """Base class for tests to make testing of branch visibility easier."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Setup some sample people and teams.

        The team names are: "xray", "yankie", and "zulu".

        The people are:

          * "albert", who is a member of all three teams.
          * "bob", who is a member of yankie.
          * "charlie", who is a member of zulu.
          * "doug", who is a member of no teams.
        """
        TestCase.setUp(self)
        login(ANONYMOUS)
        # Our test product.
        person_set = getUtility(IPersonSet)

        self.firefox = getUtility(IProductSet).getByName('firefox')
        # Create some test people.
        self.albert, alberts_email  = person_set.createPersonAndEmail(
            'albert@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='albert', displayname='Albert Tester')
        self.albert.setPreferredEmail(alberts_email)
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

        # And create some test teams.
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

        # Set the memberships of our test people to the test teams.
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
        """Check the visibility policy for branch creation.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        :param private: The expected private flag value.
        :param subscriber: The expected implicit subscriber to the branch.
        """
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
        """Assert that the policy check results in a public branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        self.assertVisibilityPolicy(creator, owner, False, None)

    def assertPrivateSubscriber(self, creator, owner, subscriber):
        """Assert that the policy check results in a private branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        :param subscriber: The expected implicit subscriber to the branch.
        """
        self.assertVisibilityPolicy(creator, owner, True, subscriber)

    def assertBranchCreationForbidden(self, creator, owner):
        """Assert that the policy check raises BranchCreationForbidden.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        self.assertRaises(
            BranchCreationForbidden,
            BranchSet()._checkVisibilityPolicy,
            creator=creator, owner=owner, product=self.firefox)

    def assertBranchCreatorNotMemberOfOwnerTeam(self, creator, owner):
        """Assert that the policy check raises BranchCreatorNotMemberOfOwnerTeam.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
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
                        "Albert should be in team X-Ray team.")
        self.failUnless(albert.inTeam(yankie),
                        "Albert should be in the Yankie.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of only Yankie.
        self.failIf(bob.inTeam(xray),
                    "Bob should not be in team X-Ray team.")
        self.failUnless(bob.inTeam(yankie),
                        "Bob should be in the Yankie team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of only Zulu.
        self.failIf(charlie.inTeam(xray),
                    "Charlie should not be in team X-Ray team.")
        self.failIf(charlie.inTeam(yankie),
                    "Charlie should not be in the Yankie team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team X-Ray team.")
        self.failIf(doug.inTeam(yankie),
                    "Doug should not be in the Yankie team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")


class NoPolicies(BranchVisibilityPolicyTestCase):
    """Test behaviour with no policies defined."""

    def test_creation_where_not_team_member(self):
        """If the creator isn't a member of the owner an exception is raised."""
        self.assertBranchCreatorNotMemberOfOwnerTeam(self.doug, self.xray)
        self.assertBranchCreatorNotMemberOfOwnerTeam(self.albert, self.bob)

    def test_public_branch_creation(self):
        """Branches where the creator is a memeber of owner will be public."""
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams

        self.assertPublic(albert, albert)
        self.assertPublic(albert, xray)
        self.assertPublic(albert, yankie)
        self.assertPublic(albert, zulu)

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankie)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicySimple(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base policy is PUBLIC with one team
    specified to have PRIVATE branches."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_xray_branches_private(self):
        # Branches created by people in the X-Ray team will be private if in
        # thier own namespace.
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)
        # Private in X-Ray team namespace.
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_public_branches(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams

        # If Albert creates a branch for a team that isn't a member of
        # the X-Ray team, then they are public.
        self.assertPublic(albert, yankie)
        self.assertPublic(albert, zulu)

        # Branches created by people not in the X-Ray team will be public.
        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankie)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyPrivateOnly(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base policy is PUBLIC with one team
    specified to have the PRIVATE_ONLY policy.

    PRIVATE_ONLY only stops the user from changing the branch from private to
    public and for branch creation behaves in the same maner as the PRIVATE
    policy.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.xray, BranchVisibilityPolicy.PRIVATE_ONLY),
            ))

    def test_xray_branches_private(self):
        # Branches created by people in the X-Ray team will be private if in
        # thier own namespace.
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)
        # Private in X-Ray team namespace.
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_public_branches(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams

        # If Albert creates a branch for a team that isn't a member of
        # the X-Ray team, then they are public.
        self.assertPublic(albert, yankie)
        self.assertPublic(albert, zulu)

        # Branches created by people not in the X-Ray team will be public.
        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankie)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyForbidden(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base policy is FORBIDDEN with one
    team specified to have the PRIVATE branches and another team specified
    to have PUBLIC branches.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (None, BranchVisibilityPolicy.FORBIDDEN),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.yankie, BranchVisibilityPolicy.PUBLIC),
            ))

    def test_branch_creation_forbidden_non_members(self):
        """People who are not members of X-Ray or Yankie are not allowed to
        create branches.
        """
        self.assertBranchCreationForbidden(self.charlie, self.charlie)
        self.assertBranchCreationForbidden(self.charlie, self.zulu)

        self.assertBranchCreationForbidden(self.doug, self.doug)

    def test_branch_creation_forbidden_other_namespace(self):
        """People who are members of X-Ray or Yankie are not allowed to
        create branches in a namespace of a team that is not a member
        of X-Ray or Yankie.
        """
        self.assertBranchCreationForbidden(self.albert, self.zulu)

    def test_yankie_branches_public(self):
        """Branches in the yankie namespace are public."""
        self.assertPublic(self.bob, self.yankie)
        self.assertPublic(self.albert, self.yankie)

    def test_yankie_member_branches_public(self):
        """Branches created by a member of Yankie, who is not a member
        of X-Ray will be public.
        """
        self.assertPublic(self.bob, self.bob)

    def test_xray_branches_private(self):
        """Branches in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by X-Ray team members in their own namespace
        will be private, and subscribed to by the X-Ray team.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)


class PolicyTeamOverlap(BranchVisibilityPolicyTestCase):
    """Test the policy where a user is a member of multiple teams with private
    branches enabled.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.definePolicy((
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.zulu, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_public_branches_for_non_members(self):
        """Branches created by people who are not members of xray or zulu
        will be public branches.
        """
        self.assertPublic(self.bob, self.bob)
        self.assertPublic(self.bob, self.yankie)
        self.assertPublic(self.doug, self.doug)

    def test_public_branches_for_members_in_other_namespace(self):
        """If a member of xray or zulu creates a branch for a team that is
        not a member of xray or zulu, then the branch will be a public branch.
        """
        self.assertPublic(self.albert, self.yankie)

    def test_team_branches_private(self):
        """Branches created in the namespace of a team that has private
        branches specified are private.
        """
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_one_membership_private_with_subscriber(self):
        """If the creator of the branch is a member of only one team that has
        private branches set up, then that team will be subscribed to any
        branches that the creator registers in their own namespace.
        """
        self.assertPrivateSubscriber(self.charlie, self.charlie, self.zulu)

    def test_two_memberships_private_no_subscriber(self):
        """If the creator of the branch is a member of two or more teams
        that have private branches enabled, then when a branch is created
        in their own namespace, there are no implicit subscribers.

        This is done as we cannot guess which team should have access
        to the private branch.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


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

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertBranchCreationForbidden(self.doug, self.doug)

    def test_zulu_branches_public(self):
        """Branches pushed to the zulu team namespace are public branches."""
        self.assertPublic(self.albert, self.zulu)
        self.assertPublic(self.charlie, self.zulu)

    def test_zulu_members_only_public(self):
        """A user who is a member of zulu, and not a member of a team that
        specifies private branch creation have public branches when created
        in the user's own namespace.
        """
        self.assertPublic(self.charlie, self.charlie)

    def test_xray_and_yankie_branches_private(self):
        """Branches that are created in the namespace of either xray or yankie
        are private branches.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.albert, self.yankie, None)
        self.assertPrivateSubscriber(self.bob, self.yankie, None)

    def test_xray_member_private_with_subscription(self):
        """Branches created by a user who is a member of only one team that
        specifies private branches will have branches in the user's namespace
        created as private branches with the team subscribed to them.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.yankie)

    def test_multiple_memberships_private(self):
        """If the user is a member of multiple teams that specify private
        branches, then this overrides PUBLIC policy that may apply.

        Any branch created in the user's own namespace will not have any
        implicit subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


class TeamsWithinTeamsPolicies(BranchVisibilityPolicyTestCase):
    """Test the policy when teams within teams have different policies."""

    def setUp(self):
        """Join up the teams so zulu is in yankie, and yankie is in zulu."""
        BranchVisibilityPolicyTestCase.setUp(self)
        # import pdb; pdb.set_trace()
        self.yankie.addMember(self.zulu, self.albert, force_team_add=True)
        self.xray.addMember(self.yankie, self.albert, force_team_add=True)
        self.definePolicy((
            (None, BranchVisibilityPolicy.FORBIDDEN),
            (self.xray, BranchVisibilityPolicy.PRIVATE),
            (self.yankie, BranchVisibilityPolicy.PUBLIC),
            (self.zulu, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankie, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team X-Ray team.")
        self.failUnless(albert.inTeam(yankie),
                        "Albert should be in the Yankie.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of Yankie, and now X-Ray.
        self.failUnless(bob.inTeam(xray),
                        "Bob should now be in team X-Ray team.")
        self.failUnless(bob.inTeam(yankie),
                        "Bob should be in the Yankie team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of Zulu, and through Zulu a member
        # of Yankie, and through Yankie a member of X-Ray.
        self.failUnless(charlie.inTeam(xray),
                        "Charlie should now be in team X-Ray team.")
        self.failUnless(charlie.inTeam(yankie),
                        "Charlie should now be in the Yankie team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team X-Ray team.")
        self.failIf(doug.inTeam(yankie),
                    "Doug should not be in the Yankie team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertBranchCreationForbidden(self.doug, self.doug)

    def test_xray_and_zulu_branches_private_no_subscriber(self):
        """All branches created in the namespace of teams that specify
        private branches are private with no subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.bob, self.xray, None)
        self.assertPrivateSubscriber(self.charlie, self.xray, None)

        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)

    def test_yankie_branches_public(self):
        """All branches created in the namespace of teams that specify
        public branches are public.
        """
        self.assertPublic(self.albert, self.yankie)
        self.assertPublic(self.bob, self.yankie)
        self.assertPublic(self.charlie, self.yankie)

    def test_privacy_through_team_membership_of_private_team(self):
        """Policies that apply to team apply to people that are members
        indirectly in the same way as direct membership.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.xray)

    def test_multiple_private_policies_through_indirect_membership(self):
        """If a person is a member of a team that specifies private branches,
        and that team is also a member either directly or indirectly of another
        team that specifies private branches, then when members of those teams
        create branches, those branches have no implicit subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)
        self.assertPrivateSubscriber(self.charlie, self.charlie, None)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
