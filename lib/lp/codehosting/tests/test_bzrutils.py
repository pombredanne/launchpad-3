# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for bzrutils."""

__metaclass__ = type

import gc

from bzrlib import errors
from bzrlib.branch import Branch
from bzrlib.bzrdir import format_registry
from bzrlib.tests import (
    TestCaseWithTransport, TestLoader, TestNotApplicable)
from bzrlib.tests.branch_implementations import TestCaseWithBzrDir
from lp.codehosting.bzrutils import (
    DenyingServer, get_branch_stacked_on_url, is_branch_stackable)
from lp.codehosting.tests.helpers import TestResultWrapper


class TestGetBranchStackedOnURL(TestCaseWithBzrDir):
    """Tests for get_branch_stacked_on_url()."""

    def __str__(self):
        """Return the test id so that Zope test output shows the format."""
        return self.id()

    def tearDown(self):
        # This makes sure the connections held by the branches opened in the
        # test are dropped, so the daemon threads serving those branches can
        # exit.
        gc.collect()
        TestCaseWithBzrDir.tearDown(self)

    def run(self, result=None):
        """Run the test, with the result wrapped so that it knows about skips.
        """
        if result is None:
            result = self.defaultTestResult()
        super(TestGetBranchStackedOnURL, self).run(TestResultWrapper(result))

    def testGetBranchStackedOnUrl(self):
        # get_branch_stacked_on_url returns the URL of the stacked-on branch.
        stacked_on_branch = self.make_branch('stacked-on')
        stacked_branch = self.make_branch('stacked')
        try:
            stacked_branch.set_stacked_on_url('../stacked-on')
        except errors.UnstackableBranchFormat:
            raise TestNotApplicable('This format does not support stacking.')
        # Deleting the stacked-on branch ensures that Bazaar will raise an
        # error if it tries to open the stacked-on branch.
        self.get_transport('.').delete_tree('stacked-on')
        self.assertEqual(
            '../stacked-on',
            get_branch_stacked_on_url(stacked_branch.bzrdir))

    def testGetBranchStackedOnUrlUnstackable(self):
        # get_branch_stacked_on_url raises UnstackableBranchFormat if it's
        # called on the bzrdir of a branch that cannot be stacked.
        branch = self.make_branch('source')
        try:
            branch.get_stacked_on_url()
        except errors.NotStacked:
            raise TestNotApplicable('This format supports stacked branches.')
        except errors.UnstackableBranchFormat:
            pass
        self.assertRaises(
            errors.UnstackableBranchFormat,
            get_branch_stacked_on_url, branch.bzrdir)

    def testGetBranchStackedOnUrlNotStacked(self):
        # get_branch_stacked_on_url raises NotStacked if it's called on the
        # bzrdir of a non-stacked branch.
        branch = self.make_branch('source')
        try:
            branch.get_stacked_on_url()
        except errors.NotStacked:
            pass
        except errors.UnstackableBranchFormat:
            raise TestNotApplicable(
                'This format does not support stacked branches')
        self.assertRaises(
            errors.NotStacked, get_branch_stacked_on_url, branch.bzrdir)

    def testGetBranchStackedOnUrlNoBranch(self):
        # get_branch_stacked_on_url raises a NotBranchError if it's called on
        # a bzrdir that's not got a branch.
        a_bzrdir = self.make_bzrdir('source')
        if a_bzrdir.has_branch():
            raise TestNotApplicable(
                'This format does not support branchless bzrdirs.')
        self.assertRaises(
            errors.NotBranchError, get_branch_stacked_on_url, a_bzrdir)


class TestIsBranchStackable(TestCaseWithTransport):
    """Tests for is_branch_stackable."""

    def test_packs_unstackable(self):
        # The original packs are unstackable.
        branch = self.make_branch(
            'branch', format=format_registry.get("pack-0.92")())
        self.assertFalse(is_branch_stackable(branch))

    def test_1_9_stackable(self):
        # The original packs are unstackable.
        branch = self.make_branch(
            'branch', format=format_registry.get("1.9")())
        self.assertTrue(is_branch_stackable(branch))


class TestDenyingServer(TestCaseWithTransport):
    """Tests for `DenyingServer`."""

    def test_denyingServer(self):
        # DenyingServer prevents creations of transports for the given URL
        # schemes between setUp() and tearDown().
        branch = self.make_branch('branch')
        self.assertTrue(
            branch.base.startswith('file://'),
            "make_branch() didn't make branch with file:// URL")
        file_denier = DenyingServer(['file://'])
        file_denier.setUp()
        self.assertRaises(AssertionError, Branch.open, branch.base)
        file_denier.tearDown()
        # This is just "assertNotRaises":
        Branch.open(branch.base)


def load_tests(basic_tests, module, loader):
    """Parametrize the tests of get_branch_stacked_on_url by branch format."""
    result = loader.suiteClass()

    get_branch_stacked_on_url_tests = loader.loadTestsFromTestCase(
        TestGetBranchStackedOnURL)

    from bzrlib.tests import multiply_tests
    from bzrlib.tests.branch_implementations import branch_scenarios

    scenarios = [scenario for scenario in branch_scenarios()
                 if scenario[0] != 'BranchReferenceFormat']
    multiply_tests(get_branch_stacked_on_url_tests, scenarios, result)

    result.addTests(loader.loadTestsFromTestCase(TestIsBranchStackable))
    result.addTests(loader.loadTestsFromTestCase(TestDenyingServer))
    return result


def test_suite():
    loader = TestLoader()
    return loader.loadTestsFromName(__name__)
