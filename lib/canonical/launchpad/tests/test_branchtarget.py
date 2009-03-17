# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchtarget import (
    PackageBranchTarget, PersonBranchTarget, ProductBranchTarget)
from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    BranchVisibilityRule)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer


class BaseBranchTargetTests:

    def test_provides_IPrimaryContext(self):
        self.assertProvides(self.target, IPrimaryContext)

    def test_context(self):
        # IBranchTarget.context is the original object.
        self.assertEqual(self.original, self.target.context)

    def test_canonical_url(self):
        # The canonical URL of a branch target is the canonical url of its
        # context.
        self.assertEqual(
            canonical_url(self.original), canonical_url(self.target))


class TestPackageBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeSourcePackage()
        self.target = PackageBranchTarget(self.original)

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        self.assertEqual(self.original.path, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(self.original, namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(self.target, PackageBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual(
            [self.original.distribution, self.original.distroseries,
             self.original],
            list(target.components))


class TestPersonBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makePerson()
        self.target = PersonBranchTarget(self.original)

    def test_name(self):
        # The name of a junk context is '+junk'.
        self.assertEqual('+junk', self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        namespace = self.target.getNamespace(self.original)
        self.assertEqual(namespace.owner, self.original)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, PersonBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual([self.original], list(target.components))


class TestProductBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeProduct()
        self.target = ProductBranchTarget(self.original)

    def test_name(self):
        self.assertEqual(self.original.name, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(namespace.product, self.original)
        self.assertEqual(namespace.owner, person)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, ProductBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual([self.original], list(target.components))


class TestPrimaryContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_package_branch(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_product_branch(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))


class TestPersonBranchTargetCanCreateBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_individual(self):
        # For a BranchTarget for an individual, only the individual can own
        # branches there.
        person = self.factory.makePerson()
        target = IBranchTarget(person)
        self.assertTrue(target.canCreateBranches(person))

    def test_other_user(self):
        # Any other individual cannot own branches targetted to the person.
        person = self.factory.makePerson()
        target = IBranchTarget(person)
        self.assertFalse(target.canCreateBranches(self.factory.makePerson()))

    def test_team_member(self):
        # A member of a team is able to create a branch on this namespace.
        # This is a team junk branch.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        target = IBranchTarget(team)
        self.assertTrue(target.canCreateBranches(person))

    def test_team_non_member(self):
        # A person who is not part of the team cannot create branches for the
        # personal team target.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        target = IBranchTarget(team)
        self.assertFalse(target.canCreateBranches(self.factory.makePerson()))


class TestSourcePackageBranchTargetCanCreateBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_any_person(self):
        # There is no privicy for source packages at this stage, so any user
        # can create a branch on a SourcePackageBranchTarget.
        source_package = self.factory.makeSourcePackage()
        target = IBranchTarget(source_package)
        self.assertTrue(target.canCreateBranches(self.factory.makePerson()))


class TestProductBranchTargetCanCreateBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Setting visibility policies is an admin only task.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self.product = self.factory.makeProduct()
        self.target = IBranchTarget(self.product)

    def test_any_person(self):
        # If there is no privacy set up, any person can create a branch on the
        # product.
        self.assertTrue(
            self.target.canCreateBranches(self.factory.makePerson()))

    def test_any_person_with_public_base_rule(self):
        # If the base visibility rule is PUBLIC, then anyone can create a
        # branch.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertTrue(
            self.target.canCreateBranches(self.factory.makePerson()))

    def test_any_person_with_forbidden_base_rule(self):
        # If the base visibility rule is FORBIDDEN, then non-privleged users
        # canot create a branch.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertFalse(
            self.target.canCreateBranches(self.factory.makePerson()))

    def assertTeamMemberCanCreateBranches(self, policy_rule):
        # Create a product with a team policy with the specified rule, and
        # make sure that the team member can create branches.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.product.setBranchVisibilityTeamPolicy(team, policy_rule)
        self.assertTrue(self.target.canCreateBranches(person))

    def test_team_member_public_policy(self):
        # A person in a team with a PUBLIC rule can create branches even if
        # the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(BranchVisibilityRule.PUBLIC)

    def test_team_member_private_policy(self):
        # A person in a team with a PRIVATE rule can create branches even if
        # the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(BranchVisibilityRule.PRIVATE)

    def test_team_member_private_only_policy(self):
        # A person in a team with a PRIVATE_ONLY rule can create branches even
        # if the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(
            BranchVisibilityRule.PRIVATE_ONLY)


class TestPersonBranchTargetAreNewBranchesPrivate(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # No +junk branches are private.
        person = self.factory.makePerson()
        target = IBranchTarget(person)
        self.assertFalse(target.areNewBranchesPrivate(person))


class TestSourcePackageBranchTargetAreNewBranchesPrivate(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # No source package branches are private.
        source_package = self.factory.makeSourcePackage()
        target = IBranchTarget(source_package)
        self.assertFalse(
            target.areNewBranchesPrivate(self.factory.makePerson()))


class TestProductBranchTargetAreNewBranchesPrivate(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.product = self.factory.makeProduct()
        self.target = IBranchTarget(self.product)

    def test_no_policies(self):
        # If there are no defined policies, the branches are not private.
        self.assertFalse(
            self.target.areNewBranchesPrivate(self.factory.makePerson()))

    def test_any_person_with_public_base_rule(self):
        # If the base visibility rule is PUBLIC, then new branches are public.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertFalse(
            self.target.areNewBranchesPrivate(self.factory.makePerson()))

    def test_any_person_with_forbidden_base_rule(self):
        # If the base visibility rule is FORBIDDEN, new branches are still
        # considered public.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertFalse(
            self.target.areNewBranchesPrivate(self.factory.makePerson()))

    def test_team_member_with_private_rule(self):
        # If a person is a member of a team that has a PRIVATE rule, then new
        # branches are private.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertTrue(self.target.areNewBranchesPrivate(person))

    def test_team_member_with_private_only_rule(self):
        # If a person is a member of a team that has a PRIVATE_ONLY rule, then
        # new branches are private.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertTrue(self.target.areNewBranchesPrivate(person))

    def test_non_team_member_with_private_rule(self):
        # If a person is a not a member of a team that has a privacy rule,
        # then new branches are public.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertFalse(
            self.target.areNewBranchesPrivate(self.factory.makePerson()))

    def test_team_member_with_multiple_private_rules(self):
        # If a person is a member of multiple teams that has a privacy rules,
        # then new branches are private.
        person = self.factory.makePerson()
        self.product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PRIVATE)
        self.product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PRIVATE)
        self.assertTrue(self.target.areNewBranchesPrivate(person))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
