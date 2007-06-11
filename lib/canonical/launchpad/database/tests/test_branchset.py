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


class BranchSetVisibilityPolicySimple(TestCase):
    """Test the policy where Public for all except one team where private."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        self.firefox = getUtility(IProductSet).getByName('firefox')
        self.guadamen = getUtility(IPersonSet).getByName('guadamen')
        self.firefox.setTeamBranchVisibilityPolicy(
            None, BranchVisibilityPolicy.PUBLIC)
        self.firefox.setTeamBranchVisibilityPolicy(
            self.guadamen, BranchVisibilityPolicy.PRIVATE)

    def test_public_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        branch_set = BranchSet()
        ddaa = getUtility(IPersonSet).getByEmail('david@canonical.com')
        self.failUnless(not ddaa.inTeam(self.guadamen),
                        "David should not be in team Guadamen.")
        create_private, implicit_subscription_team = (
            BranchSet()._checkVisibilityPolicy(
            creator=ddaa, owner=ddaa, product=self.firefox))
        self.failUnless(not create_private, "Branch should be created public.")
        self.failUnless(
            implicit_subscription_team is None,
            "There should be no implict subscriptions for public branches.")

    def test_private_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        branch_set = BranchSet()
        foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        self.failUnless(foo_bar.inTeam(self.guadamen),
                        "Foo Bar should be in team Guadamen.")
        create_private, implicit_subscription_team = (
            BranchSet()._checkVisibilityPolicy(
            creator=foo_bar, owner=foo_bar, product=self.firefox))
        self.failUnless(create_private, "Branch should be created private.")
        self.assertEqual(
            implicit_subscription_team, self.guadamen,
            "Guadamen should be subscribed to branches created by Foo Bar.")


class BranchSetVisibilityPolicyForbidden(TestCase):
    """Test the policy where Forbidden for all, public for some and private
    for others.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        self.firefox = getUtility(IProductSet).getByName('firefox')
        self.guadamen = getUtility(IPersonSet).getByName('guadamen')
        self.ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
        self.firefox.setTeamBranchVisibilityPolicy(
            None, BranchVisibilityPolicy.FORBIDDEN)
        self.firefox.setTeamBranchVisibilityPolicy(
            self.guadamen, BranchVisibilityPolicy.PRIVATE)
        self.firefox.setTeamBranchVisibilityPolicy(
            self.ubuntu_team, BranchVisibilityPolicy.PUBLIC)

    def test_forbidden_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        branch_set = BranchSet()
        ddaa = getUtility(IPersonSet).getByEmail('david@canonical.com')
        self.failUnless(not ddaa.inTeam(self.guadamen),
                        "David should not be in team Guadamen.")
        self.failUnless(not ddaa.inTeam(self.ubuntu_team),
                        "David should not be in the Ubuntu team.")
        self.assertRaises(
            BranchCreationForbidden,
            BranchSet()._checkVisibilityPolicy,
            creator=ddaa, owner=ddaa, product=self.firefox)

    def test_public_branch_creation(self):
        """Branches created by people in the Ubuntu team will be public."""
        branch_set = BranchSet()
        stevea = getUtility(IPersonSet).getByName('stevea')
        self.failUnless(not stevea.inTeam(self.guadamen),
                        "Steve should not be in team Guadamen.")
        self.failUnless(stevea.inTeam(self.ubuntu_team),
                        "Steve should be in the Ubuntu team.")
        create_private, implicit_subscription_team = (
            BranchSet()._checkVisibilityPolicy(
            creator=stevea, owner=stevea, product=self.firefox))
        self.failUnless(not create_private, "Branch should be created public.")
        self.failUnless(
            implicit_subscription_team is None,
            "There should be no implict subscriptions for public branches.")

    def test_private_branch_creation(self):
        """Branches created by people not in Guadamen will be public."""
        branch_set = BranchSet()
        foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        self.failUnless(foo_bar.inTeam(self.guadamen),
                        "Foo Bar should be in team Guadamen.")
        create_private, implicit_subscription_team = (
            BranchSet()._checkVisibilityPolicy(
            creator=foo_bar, owner=foo_bar, product=self.firefox))
        self.failUnless(create_private, "Branch should be created private.")
        self.assertEqual(
            implicit_subscription_team, self.guadamen,
            "Guadamen should be subscribed to branches created by Foo Bar.")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
