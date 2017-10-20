# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestProjectBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectBranches, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.product = self.factory.makeProduct(projectgroup=self.projectgroup)

    def test_has_branches_with_no_branches(self):
        # If there are no product branches on the project group's products,
        # then has_branches returns False.
        self.assertFalse(self.projectgroup.has_branches())

    def test_has_branches_with_branches(self):
        # If a product has a branch, then the product's project group
        # returns true for has_branches.
        self.factory.makeProductBranch(product=self.product)
        self.assertTrue(self.projectgroup.has_branches())
