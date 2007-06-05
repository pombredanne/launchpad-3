# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for codehosting tests."""

__metaclass__ = type
__all__ = [
    'AvatarTestCase', 'CodeHostingTestProviderAdapter',
    'CodeHostingRepositoryTestProviderAdapter', 'FakeLaunchpad',
    'TwistedBzrlibLayer', 'adapt_suite', 'deferToThread']

import os
import shutil
import threading
import unittest

from canonical.testing import TwistedLayer, BzrlibLayer
from canonical.tests.test_twisted import TwistedTestCase

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata


class AvatarTestCase(TwistedTestCase):
    """Base class for tests that need a LaunchpadAvatar with some basic sample
    data.
    """

    def setUp(self):
        self.tmpdir = self.mktemp()
        os.mkdir(self.tmpdir)
        # A basic user dict, 'alice' is a member of no teams (aside from the
        # user themself).
        self.aliceUserDict = {
            'id': 1,
            'name': 'alice',
            'teams': [{'id': 1, 'name': 'alice', 'initialBranches': []}],
        }

        # An slightly more complex user dict for a user, 'bob', who is also a
        # member of a team.
        self.bobUserDict = {
            'id': 2,
            'name': 'bob',
            'teams': [{'id': 2, 'name': 'bob', 'initialBranches': []},
                      {'id': 3, 'name': 'test-team', 'initialBranches': []}],
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

        # Remove test droppings in the current working directory from using
        # twisted.trial.unittest.TestCase.mktemp outside the trial test runner.
        tmpdir_root = self.tmpdir.split(os.sep, 1)[0]
        shutil.rmtree(tmpdir_root)


class TwistedBzrlibLayer(TwistedLayer, BzrlibLayer):
    """Use the Twisted reactor and Bazaar's temporary directory logic."""


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


class FakeLaunchpad:
    """Stub RPC interface to Launchpad."""

    def __init__(self):
        self._person_set = {
            1: dict(name='testuser', displayname='Test User',
                    emailaddresses=['test@test.com'], wikiname='TestUser',
                    teams=[1, 2]),
            2: dict(name='testteam', displayname='Test Team', teams=[]),
            }
        self._product_set = {
            1: dict(name='firefox'),
            2: dict(name='thunderbird'),
            }
        self._branch_set = {}
        self.createBranch(1, 1, 'baz')
        self.createBranch(1, 1, 'qux')
        self.createBranch(1, '', 'random')
        self.createBranch(2, 1, 'qux')

    def _lookup(self, item_set, item_id):
        row = dict(item_set[item_id])
        row['id'] = item_id
        return row

    def _insert(self, item_set, item_dict):
        new_id = max(item_set.keys() + [0]) + 1
        item_set[new_id] = item_dict
        return new_id

    def createBranch(self, user_id, product_id, branch_name):
        """See IHostedBranchStorage.createBranch."""
        new_branch = dict(
            name=branch_name, user_id=user_id, product_id=product_id)
        for branch in self._branch_set.values():
            if branch == new_branch:
                raise ValueError("Already have branch: %r" % (new_branch,))
        return self._insert(self._branch_set, new_branch)

    def fetchProductID(self, name):
        """See IHostedBranchStorage.fetchProductID."""
        if name == '+junk':
            return ''
        for product_id, product_info in self._product_set.iteritems():
            if product_info['name'] == name:
                return product_id
        return None

    def getUser(self, loginID):
        """See IUserDetailsStorage.getUser."""
        matching_user_id = None
        for user_id, user_dict in self._person_set.iteritems():
            loginIDs = [user_id, user_dict['name']]
            loginIDs.extend(user_dict.get('emailaddresses', []))
            if loginID in loginIDs:
                matching_user_id = user_id
                break
        if matching_user_id is None:
            return ''
        user_dict = self._lookup(self._person_set, matching_user_id)
        user_dict['teams'] = [
            self._lookup(self._person_set, id) for id in user_dict['teams']]
        return user_dict

    def getBranchesForUser(self, personID):
        """See IHostedBranchStorage.getBranchesForUser."""
        product_branches = {}
        for branch_id, branch in self._branch_set.iteritems():
            if branch['user_id'] != personID:
                continue
            product_branches.setdefault(
                branch['product_id'], []).append((branch_id, branch['name']))
        result = []
        for product, branches in product_branches.iteritems():
            if product == '':
                result.append(('', '', branches))
            else:
                result.append(
                    (product, self._product_set[product]['name'], branches))
        return result


class CodeHostingTestProviderAdapter:

    def __init__(self, servers):
        self._servers = servers

    def adaptForServer(self, test, server):
        from copy import deepcopy
        new_test = deepcopy(test)
        new_test.installServer(server)
        def make_new_test_id():
            new_id = "%s(%s)" % (new_test.id(), server._schema)
            return lambda: new_id
        new_test.id = make_new_test_id()
        return new_test

    def adapt(self, test):
        result = unittest.TestSuite()
        for server in self._servers:
            new_test = self.adaptForServer(test, server)
            result.addTest(new_test)
        return result


class CodeHostingRepositoryTestProviderAdapter(CodeHostingTestProviderAdapter):

    def __init__(self, format, servers):
        self._repository_format = format
        CodeHostingTestProviderAdapter.__init__(self, servers)

    def adaptForServer(self, test, server):
        from bzrlib.tests import default_transport
        new_test = CodeHostingTestProviderAdapter.adaptForServer(
            self, test, server)
        new_test.transport_server = default_transport
        new_test.transport_readonly_server = None
        new_test.bzrdir_format = self._repository_format._matchingbzrdir
        new_test.repository_format = self._repository_format
        return new_test


def adapt_suite(adapter, base_suite):
    from bzrlib.tests import iter_suite_tests
    suite = unittest.TestSuite()
    for test in iter_suite_tests(base_suite):
        suite.addTests(adapter.adapt(test))
    return suite
