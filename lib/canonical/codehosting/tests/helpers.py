# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for codehosting tests."""

__metaclass__ = type
__all__ = [
    'AvatarTestCase',
    'adapt_suite',
    'BranchTestCase',
    'CodeHostingTestProviderAdapter',
    'CodeHostingRepositoryTestProviderAdapter',
    'create_branch_with_one_revision',
    'deferToThread',
    'LoomTestMixin',
    'make_bazaar_branch_and_tree',
    'ServerTestCase',
    'TestResultWrapper',
    ]

import os
import threading
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import FileExists, PermissionDenied, TransportNotPossible
from bzrlib.plugins.loom import branch as loom_branch
from bzrlib.tests import TestCaseWithTransport, TestNotApplicable, TestSkipped
from bzrlib.errors import SmartProtocolError

from canonical.codehosting.branchfs import branch_id_to_path
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.testing import TwistedLayer

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata
from twisted.trial.unittest import TestCase as TrialTestCase


class AvatarTestCase(TrialTestCase):
    """Base class for tests that need a LaunchpadAvatar with some basic sample
    data.
    """

    layer = TwistedLayer

    def setUp(self):
        # A basic user dict, 'alice' is a member of no teams (aside from the
        # user themself).
        self.aliceUserDict = {
            'id': 1,
            'name': 'alice',
            'teams': [{'id': 1, 'name': 'alice'}],
            'initialBranches': [(1, [])]
        }

        # An slightly more complex user dict for a user, 'bob', who is also a
        # member of a team.
        self.bobUserDict = {
            'id': 2,
            'name': 'bob',
            'teams': [{'id': 2, 'name': 'bob'},
                      {'id': 3, 'name': 'test-team'}],
            'initialBranches': [(2, []), (3, [])]
        }


def exception_names(exceptions):
    """Return a list of exception names for the given exception list."""
    if isinstance(exceptions, tuple):
        names = []
        for exc in exceptions:
            names.extend(exception_names(exc))
    elif exceptions is TransportNotPossible:
        # Unfortunately, not all exceptions render themselves as their name.
        # More cases like this may need to be added
        names = ["Transport operation not possible"]
    elif exceptions is PermissionDenied:
        names = ['Permission denied', 'PermissionDenied']
    else:
        names = [exceptions.__name__]
    return names


class LoomTestMixin:
    """Mixin to provide Bazaar test classes with limited loom support."""

    def loomify(self, branch):
        tree = branch.create_checkout('checkout')
        tree.lock_write()
        try:
            tree.branch.nick = 'bottom-thread'
            loom_branch.loomify(tree.branch)
        finally:
            tree.unlock()
        loom_tree = tree.bzrdir.open_workingtree()
        loom_tree.lock_write()
        loom_tree.branch.new_thread('bottom-thread')
        loom_tree.commit('this is a commit', rev_id='commit-1')
        loom_tree.unlock()
        loom_tree.branch.record_loom('sample loom')
        self.get_transport().delete_tree('checkout')
        return loom_tree

    def makeLoomBranchAndTree(self, tree_directory):
        """Make a looms-enabled branch and working tree."""
        tree = self.make_branch_and_tree(tree_directory)
        tree.lock_write()
        try:
            tree.branch.nick = 'bottom-thread'
            loom_branch.loomify(tree.branch)
        finally:
            tree.unlock()
        loom_tree = tree.bzrdir.open_workingtree()
        loom_tree.lock_write()
        loom_tree.branch.new_thread('bottom-thread')
        loom_tree.commit('this is a commit', rev_id='commit-1')
        loom_tree.unlock()
        loom_tree.branch.record_loom('sample loom')
        return loom_tree


class ServerTestCase(TestCaseWithTransport, LoomTestMixin):

    server = None

    def getDefaultServer(self):
        raise NotImplementedError("No default server")

    def installServer(self, server):
        self.server = server

    def setUp(self):
        super(ServerTestCase, self).setUp()

        if self.server is None:
            self.installServer(self.getDefaultServer())

        self.server.setUp()
        self.addCleanup(self.server.tearDown)

    def __str__(self):
        return self.id()

    def assertTransportRaises(self, exception, f, *args, **kwargs):
        """A version of assertRaises() that also catches SmartProtocolError.

        If SmartProtocolError is raised, the error message must
        contain the exception name.  This is to cover Bazaar's
        handling of unexpected errors in the smart server.
        """
        # XXX: JamesHenstridge 2007-10-08 bug=118736
        # This helper should not be needed, but some of the exceptions
        # we raise (such as PermissionDenied) are not yet handled by
        # the smart server protocol as of bzr-0.91.
        names = exception_names(exception)
        try:
            f(*args, **kwargs)
        except SmartProtocolError, inst:
            for name in names:
                if name in str(inst):
                    break
            else:
                raise self.failureException("%s not raised" % names)
            return inst
        except exception, inst:
            return inst
        else:
            raise self.failureException("%s not raised" % names)

    def getTransport(self, relpath=None):
        return self.server.getTransport(relpath)


def deferToThread(f):
    """Run the given callable in a separate thread and return a Deferred which
    fires when the function completes.
    """
    def decorated(*args, **kwargs):
        d = defer.Deferred()
        def runInThread():
            return threads._putResultInDeferred(d, f, args, kwargs)

        t = threading.Thread(target=runInThread)
        t.start()
        return d
    return mergeFunctionMetadata(f, decorated)


def clone_test(test, new_id):
    """Return a clone of the given test."""
    from copy import deepcopy
    new_test = deepcopy(test)
    def make_new_test_id():
        return lambda: new_id
    new_test.id = make_new_test_id()
    return new_test


class CodeHostingTestProviderAdapter:
    """Test adapter to run a single test against many codehosting servers."""

    def __init__(self, servers):
        self._servers = servers

    def adaptForServer(self, test, serverFactory):
        server = serverFactory()
        new_test = clone_test(test, '%s(%s)' % (test.id(), server._schema))
        new_test.installServer(server)
        return new_test

    def adapt(self, test):
        result = unittest.TestSuite()
        for server in self._servers:
            new_test = self.adaptForServer(test, server)
            result.addTest(new_test)
        return result


def make_bazaar_branch_and_tree(db_branch):
    """Make a dummy Bazaar branch and working tree from a database Branch."""
    assert db_branch.branch_type == BranchType.HOSTED, (
        "Can only create branches for HOSTED branches: %r"
        % db_branch)
    branch_dir = os.path.join(
        config.codehosting.branches_root, branch_id_to_path(db_branch.id))
    return create_branch_with_one_revision(branch_dir)


def adapt_suite(adapter, base_suite):
    from bzrlib.tests import iter_suite_tests
    suite = unittest.TestSuite()
    for test in iter_suite_tests(base_suite):
        suite.addTests(adapter.adapt(test))
    return suite


def create_branch_with_one_revision(branch_dir):
    """Create a dummy Bazaar branch at the given directory."""
    if not os.path.exists(branch_dir):
        os.makedirs(branch_dir)
    try:
        tree = BzrDir.create_standalone_workingtree(branch_dir)
    except FileExists:
        return
    f = open(os.path.join(branch_dir, 'hello'), 'w')
    f.write('foo')
    f.close()
    tree.commit('message')
    return tree


class TestResultWrapper:
    """A wrapper for `TestResult` that knows about bzrlib's `TestSkipped`."""

    def __init__(self, result):
        self.result = result

    def addError(self, test_case, exc_info):
        if not isinstance(exc_info[1], (TestSkipped, TestNotApplicable)):
            self.result.addError(test_case, exc_info)

    def addFailure(self, test_case, exc_info):
        self.result.addFailure(test_case, exc_info)

    def addSuccess(self, test_case):
        self.result.addSuccess(test_case)

    def startTest(self, test_case):
        self.result.startTest(test_case)

    def stopTest(self, test_case):
        self.result.stopTest(test_case)
