# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for bzrutils."""

__metaclass__ = type

import gc

from bzrlib.branch import Branch
from bzrlib import errors
from bzrlib.tests import (
    TestCaseWithTransport, TestLoader, TestNotApplicable)
from bzrlib.tests.branch_implementations import TestCaseWithBzrDir
from canonical.codehosting.bzrutils import (
    DenyingServer, get_branch_stacked_on_url)
from canonical.codehosting.tests.helpers import TestResultWrapper


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

    try:
        from bzrlib.tests import multiply_tests
        from bzrlib.tests.branch_implementations import branch_scenarios

        scenarios = [scenario for scenario in branch_scenarios()
                     if scenario[0] != 'BranchReferenceFormat']
        multiply_tests(
            get_branch_stacked_on_url_tests, scenarios, result)
    except ImportError:
        # XXX: MichaelHudson, 2009-03-11: This except clause can be deleted
        # once sourcecode/bzr has bzr.dev r4110.
        from bzrlib.branch import (
            BranchFormat, BranchReferenceFormat, _legacy_formats)
        from bzrlib.tests import adapt_tests
        from bzrlib.tests.branch_implementations import (
            BranchTestProviderAdapter)
        from bzrlib.tests.bzrdir_implementations import (
            BzrDirTestProviderAdapter)
        from bzrlib.transport.memory import MemoryServer

        # Generate a list of branch formats and their associated bzrdir
        # formats to use.
        combinations = [(format, format._matchingbzrdir)
                        for format in
                        BranchFormat._formats.values() + _legacy_formats
                        if format != BranchReferenceFormat()]
        adapter = BranchTestProviderAdapter(
            # None here will cause the default vfs transport server to be
            # used.
            None,
            # None here will cause a readonly decorator to be created
            # by the TestCaseWithTransport.get_readonly_transport method.
            None,
            combinations)
        # add the tests for the sub modules
        adapt_tests(get_branch_stacked_on_url_tests, adapter, result)

        # This will always add the tests for smart server transport,
        # regardless of the --transport option the user specified to 'bzr
        # selftest'.
        from bzrlib.smart.server import (
            ReadonlySmartTCPServer_for_testing,
            ReadonlySmartTCPServer_for_testing_v2_only,
            SmartTCPServer_for_testing,
            SmartTCPServer_for_testing_v2_only,
            )
        from bzrlib.remote import RemoteBzrDirFormat

        # test the remote server behaviour using a MemoryTransport
        smart_server_suite = loader.suiteClass()
        adapt_to_smart_server = BzrDirTestProviderAdapter(
            MemoryServer,
            SmartTCPServer_for_testing,
            ReadonlySmartTCPServer_for_testing,
            [(RemoteBzrDirFormat())],
            name_suffix='-default')
        adapt_tests(
            get_branch_stacked_on_url_tests, adapt_to_smart_server,
            smart_server_suite)
        adapt_to_smart_server = BzrDirTestProviderAdapter(
            MemoryServer,
            SmartTCPServer_for_testing_v2_only,
            ReadonlySmartTCPServer_for_testing_v2_only,
            [(RemoteBzrDirFormat())],
            name_suffix='-v2')
        adapt_tests(
            get_branch_stacked_on_url_tests,
            adapt_to_smart_server, smart_server_suite)
        result.addTests(smart_server_suite)

    result.addTests(loader.loadTestsFromTestCase(TestDenyingServer))
    return result


def test_suite():
    loader = TestLoader()
    return loader.loadTestsFromName(__name__)
