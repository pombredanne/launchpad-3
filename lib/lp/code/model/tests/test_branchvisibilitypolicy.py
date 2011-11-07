# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchVisibilityPolicy."""

__metaclass__ = type

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.enums import BranchVisibilityRule
from lp.code.interfaces.branchvisibilitypolicy import (
    IHasBranchVisibilityPolicy,
    InvalidVisibilityPolicy,
    )
from lp.testing import TestCaseWithFactory


class TestIHasBranchVisibilityPolicy(TestCaseWithFactory):
    """Tests for `IHasBranchVisibilityPolicy`."""

    layer = DatabaseFunctionalLayer

    def test_product_implements_IHasBranchVisibilityPolicy(self):
        # Products can have visibility policies.
        product = self.factory.makeProduct()
        verifyObject(IHasBranchVisibilityPolicy, product)

    def test_project_implements_IHasBranchVisibilityPolicy(self):
        # Products can have visibility policies.
        project = self.factory.makeProject()
        verifyObject(IHasBranchVisibilityPolicy, project)


class TestBaseBranchVisibilityRules(TestCaseWithFactory):
    """Tests for `getBaseBranchVisibilityRule`."""

    layer = DatabaseFunctionalLayer

    def test_no_rules(self):
        # If there are no rules specified, the default is PUBLIC.
        product = self.factory.makeProduct()
        self.assertEqual(
            BranchVisibilityRule.PUBLIC,
            product.getBaseBranchVisibilityRule())

    def test_explicit_public(self):
        # If there is an explicit public rule, then still public.
        product = self.factory.makeProduct()
        product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertEqual(
            BranchVisibilityRule.PUBLIC,
            product.getBaseBranchVisibilityRule())

    def test_explicit_forbidden(self):
        # If there is an explicit public rule, then still public.
        product = self.factory.makeProduct()
        product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertEqual(
            BranchVisibilityRule.FORBIDDEN,
            product.getBaseBranchVisibilityRule())

    def test_inherited_public(self):
        # If there is an explicit public rule, then still public.
        project = self.factory.makeProject()
        product = self.factory.makeProduct(project=project)
        project.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertEqual(
            BranchVisibilityRule.PUBLIC,
            product.getBaseBranchVisibilityRule())

    def test_inherited_forbidden(self):
        # If there is an explicit public rule, then still public.
        project = self.factory.makeProject()
        product = self.factory.makeProduct(project=project)
        project.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertEqual(
            BranchVisibilityRule.FORBIDDEN,
            product.getBaseBranchVisibilityRule())

    def test_no_default_private(self):
        # The default visibility rule cannot be PRIVATE or PRIVATE_ONLY.
        product = self.factory.makeProduct()
        self.assertRaises(
            InvalidVisibilityPolicy,
            product.setBranchVisibilityTeamPolicy,
            None, BranchVisibilityRule.PRIVATE)
        self.assertRaises(
            InvalidVisibilityPolicy,
            product.setBranchVisibilityTeamPolicy,
            None, BranchVisibilityRule.PRIVATE_ONLY)

    def test_no_forbidden_for_team(self):
        # Forbidden is only valid for everyone, not a specific person or team.
        product = self.factory.makeProduct()
        person = self.factory.makePerson()
        self.assertRaises(
            InvalidVisibilityPolicy,
            product.setBranchVisibilityTeamPolicy,
            person, BranchVisibilityRule.FORBIDDEN)
        team = self.factory.makeTeam(owner=person)
        self.assertRaises(
            InvalidVisibilityPolicy,
            product.setBranchVisibilityTeamPolicy,
            team, BranchVisibilityRule.FORBIDDEN)
