# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for BranchSet."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, IProductSet, IPersonSet)
from canonical.lp.dbschema import BranchVisibilityPolicy
from canonical.testing import LaunchpadFunctionalLayer

from zope.component import getUtility


class BranchVisibilityPolicyTestCase(TestCase):
    """Base class for tests to make testing easier."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        # Our test product.
        self.firefox = getUtility(IProductSet).getByName('firefox')
        # Test teams.
        self.guadamen = getUtility(IPersonSet).getByName('guadamen')
        self.vcs_imports = getUtility(IPersonSet).getByName('vcs-imports')
        self.ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        # Test people
        self.ddaa = getUtility(IPersonSet).getByEmail('david@canonical.com')
        self.foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        self.stevea = getUtility(IPersonSet).getByName('stevea')

    def _definePolicy(self, policies):
        """Shortcut to help define policies."""
        for team, policy in policies:
            self.firefox.setTeamBranchVisibilityPolicy(team, policy)

    def _assertVisibilityPolicy(self, creator, owner, private, subscriber):
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

    def _assertBranchCreationForbidden(self, creator, owner):
        self.assertRaises(
            BranchCreationForbidden,
            BranchSet()._checkVisibilityPolicy,
            creator=creator, owner=owner, product=self.firefox)


class TestTeamMembership(BranchVisibilityPolicyTestCase):
    """Test the team membership once."""

    def test_team_memberships(self):
        # David is a member of only vcs-imports.
        self.failIf(self.ddaa.inTeam(self.guadamen),
                    "David should not be in team Guadamen.")
        self.failIf(self.ddaa.inTeam(self.ubuntu_team),
                    "David should not be in the Ubuntu team.")
        self.failUnless(self.ddaa.inTeam(self.vcs_imports),
                        "David should be in the VCS Imports team.")
        # Steve is a member of only ubuntu-team.
        self.failIf(self.stevea.inTeam(self.guadamen),
                    "Steve should not be in team Guadamen.")
        self.failUnless(self.stevea.inTeam(self.ubuntu_team),
                        "Steve should be in the Ubuntu team.")
        self.failIf(self.stevea.inTeam(self.vcs_imports),
                    "Steve should not be in the VCS Imports team.")
        # Foo Bar is a member of all three teams.
        self.failUnless(self.foo_bar.inTeam(self.guadamen),
                        "Foo Bar should be in team Guadamen.")
        self.failUnless(self.foo_bar.inTeam(self.vcs_imports),
                        "Foo Bar should be in VCS Imports team.")
        self.failUnless(self.foo_bar.inTeam(self.ubuntu_team),
                        "Foo Bar should be in the Ubuntu team.")


class PolicySimple(BranchVisibilityPolicyTestCase):
    """Test the policy where Public for all except one team where private."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self._definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.guadamen, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_public_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.ddaa, private=False, subscriber=None)

    def test_private_branch_creation(self):
        """Branches created by people in Guadamen will be private."""
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.foo_bar, private=True,
            subscriber=self.guadamen)


class PolicyPrivateOnly(BranchVisibilityPolicyTestCase):
    """Test the policy where Public for all except one team where private.

    Private only only stops the user from changing the branch to public.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self._definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.guadamen, BranchVisibilityPolicy.PRIVATE_ONLY),
            ))

    def test_public_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.ddaa, private=False, subscriber=None)

    def test_private_branch_creation(self):
        """Branches created by people in Guadamen will be private."""
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.foo_bar, private=True,
            subscriber=self.guadamen)


class PolicyForbidden(BranchVisibilityPolicyTestCase):
    """Test the policy where Forbidden for all, public for some and private
    for others.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self._definePolicy((
            (None, BranchVisibilityPolicy.FORBIDDEN),
            (self.guadamen, BranchVisibilityPolicy.PRIVATE),
            (self.ubuntu_team, BranchVisibilityPolicy.PUBLIC),
            ))

    def test_forbidden_branch_creation(self):
        """Branches created by people not in Guadamen or Ubuntu Team is
        forbidden.
        """
        self._assertBranchCreationForbidden(creator=self.ddaa, owner=self.ddaa)

    def test_public_branch_creation(self):
        """Branches created by people in the Ubuntu team will be public."""
        self._assertVisibilityPolicy(
            creator=self.stevea, owner=self.stevea, private=False,
            subscriber=None)

    def test_private_branch_creation(self):
        """Branches created by people in Guadamen will be private."""
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.foo_bar, private=True,
            subscriber=self.guadamen)


class PolicyTeamOverlap(BranchVisibilityPolicyTestCase):
    """Test the policy where a user is a member of multiple teams."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self._definePolicy((
            (self.guadamen, BranchVisibilityPolicy.PRIVATE),
            (self.vcs_imports, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_public_branch_creation(self):
        """The base branch visibility policy is used for Steve."""
        self._assertVisibilityPolicy(
            creator=self.stevea, owner=self.stevea, private=False,
            subscriber=None)

    def test_private_branch_creation(self):
        """David is only a member of VCS Imports.

        Since David is only a member of one team, normal behaviour applies.
        VCS Imports will be subscribed to new branches created by David.
        """
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.ddaa, private=True,
            subscriber=self.vcs_imports)
        # XXX thumper 2007-06-15
        # This subscription should not be needed if we change
        # the access policy to allow *inTeam* of owner.
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.vcs_imports, private=True,
            subscriber=self.vcs_imports)

    def test_private_branch_creation_two_teams(self):
        """Foo Bar is in both private teams."""
        # Foo Bar is not subscribed when he is the owner.
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.foo_bar, private=True,
            subscriber=None)
        # Foo Bar is subscribed when he is not the owner.
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.vcs_imports, private=True,
            subscriber=self.foo_bar)
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.guadamen, private=True,
            subscriber=self.foo_bar)
        # Even pushing to a team that doesn't have private branches
        # are private
        self._assertVisibilityPolicy(
            creator=self.foo_bar, owner=self.ubuntu_team, private=True,
            subscriber=self.foo_bar)


class PolicyTeamOverlapForbidden(BranchVisibilityPolicyTestCase):
    """Test the policy where a user is a member of multiple teams."""

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self._definePolicy((
            (None, BranchVisibilityPolicy.PUBLIC),
            (self.guadamen, BranchVisibilityPolicy.FORBIDDEN),
            (self.vcs_imports, BranchVisibilityPolicy.PRIVATE),
            ))

    def test_public_branch_creation(self):
        """The base branch visibility policy is used for Steve."""
        self._assertVisibilityPolicy(
            creator=self.stevea, owner=self.stevea, private=False,
            subscriber=None)

    def test_private_branch_creation(self):
        """David is only a member of VCS Imports.

        Since David is only a member of one team, normal behaviour applies.
        VCS Imports will be subscribed to new branches created by David.
        """
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.ddaa, private=True,
            subscriber=self.vcs_imports)
        self._assertVisibilityPolicy(
            creator=self.ddaa, owner=self.vcs_imports, private=True,
            subscriber=self.vcs_imports)

    def test_private_branch_creation_two_teams(self):
        """Foo Bar is in a team with forbidden policy."""
        # Forbidden trumps all else.
        self._assertBranchCreationForbidden(
            creator=self.foo_bar, owner=self.foo_bar)
        # Since Foo Bar is a member of a team that is forbidden then
        # even creating team branches for the team that is allowed
        # private branches, or even public branches for that matter
        # is forbidden.
        self._assertBranchCreationForbidden(
            creator=self.foo_bar, owner=self.vcs_imports)
        self._assertBranchCreationForbidden(
            creator=self.foo_bar, owner=self.guadamen)
        self._assertBranchCreationForbidden(
            creator=self.foo_bar, owner=self.ubuntu_team)

        # XXX thumper 2007-06-15
        # We should really change the way that this is checked.
        # ideally some of the visibility checks should be done
        # based on the team that they are being pushed to.


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
