# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for bzrutils."""

__metaclass__ = type

from bzrlib.bzrdir import BzrDirFormat
from bzrlib.tests import adapt_tests, default_transport, TestLoader
from bzrlib.tests.bzrdir_implementations import (
    BzrDirTestProviderAdapter, TestCaseWithBzrDir)
from bzrlib.transport.memory import MemoryServer


class TestGetBranchStackedOnURL(TestCaseWithBzrDir):

    def __str__(self):
        """Return the test id so that Zope test output shows the format."""
        return self.id()

    def test_foo(self):
        pass


def load_tests(basic_tests, module, loader):
    """Parametrize the tests by BzrDir.

    This is mostly copy-and-pasted from
    bzrlib/tests/bzrdir_implementations/__init__.py.
    """
    result = loader.suiteClass()

    # Add a format that supports stacking.
    from bzrlib.bzrdir import BzrDirMetaFormat1
    from bzrlib.branch import BzrBranchFormat7
    from bzrlib.repofmt.pack_repo import RepositoryFormatKnitPack5
    stacking_format = BzrDirMetaFormat1()
    stacking_format.set_branch_format(BzrBranchFormat7())
    stacking_format.repository_format = RepositoryFormatKnitPack5()
    BzrDirFormat.register_format(stacking_format)

    formats = BzrDirFormat.known_formats()
    adapter = BzrDirTestProviderAdapter(
        default_transport,
        None,
        # None here will cause a readonly decorator to be created
        # by the TestCaseWithTransport.get_readonly_transport method.
        None,
        formats)
    # add the tests for the sub modules
    adapt_tests(basic_tests, adapter, result)

    # This will always add the tests for smart server transport, regardless of
    # the --transport option the user specified to 'bzr selftest'.
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
    adapt_tests(basic_tests, adapt_to_smart_server, smart_server_suite)
    adapt_to_smart_server = BzrDirTestProviderAdapter(
        MemoryServer,
        SmartTCPServer_for_testing_v2_only,
        ReadonlySmartTCPServer_for_testing_v2_only,
        [(RemoteBzrDirFormat())],
        name_suffix='-v2')
    adapt_tests(basic_tests, adapt_to_smart_server, smart_server_suite)
    result.addTests(smart_server_suite)
    return result


def test_suite():
    loader = TestLoader()
    return loader.loadTestsFromName(__name__)
