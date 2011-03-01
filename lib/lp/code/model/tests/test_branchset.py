# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchSet."""

__metaclass__ = type

from unittest import TestLoader

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branch import IBranchSet
from lp.code.model.branch import BranchSet
from lp.testing import TestCaseWithFactory


class TestBranchSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_set = BranchSet()

    def test_provides_IBranchSet(self):
        # BranchSet instances provide IBranchSet.
        self.assertProvides(self.branch_set, IBranchSet)

    def test_getByUrls(self):
        # getByUrls returns a list of branches matching the list of URLs that
        # it's given.
        a = self.factory.makeAnyBranch()
        b = self.factory.makeAnyBranch()
        branches = self.branch_set.getByUrls(
            [a.bzr_identity, b.bzr_identity])
        self.assertEqual({a.bzr_identity: a, b.bzr_identity: b}, branches)

    def test_getByUrls_cant_find_url(self):
        # If a branch cannot be found for a URL, then None appears in the list
        # in place of the branch.
        url = 'http://example.com/doesntexist'
        branches = self.branch_set.getByUrls([url])
        self.assertEqual({url: None}, branches)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
