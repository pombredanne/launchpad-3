# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for codehosting tests."""

__metaclass__ = type
__all__ = [
    'AvatarTestCase', 'CodeHostingTestProviderAdapter',
    'CodeHostingRepositoryTestProviderAdapter', 'FakeLaunchpad',
    'ServerTestCase', 'adapt_suite', 'deferToThread']

import os
import shutil
import signal
import threading
import unittest

import transaction

from bzrlib.tests import TestCaseWithTransport

from zope.component import getUtility
from zope.security.management import getSecurityPolicy, setSecurityPolicy
from zope.security.simplepolicies import PermissiveSecurityPolicy

from canonical.database.sqlbase import cursor
from canonical.launchpad.interfaces import (
    BranchType, IBranchSet, IPersonSet, IProductSet, PersonCreationRationale,
    UnknownBranchTypeError)
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing import LaunchpadFunctionalLayer
from canonical.tests.test_twisted import TwistedTestCase

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata
from twisted.trial.unittest import TestCase as TrialTestCase


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

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

        # Remove test droppings in the current working directory from using
        # twisted.trial.unittest.TestCase.mktemp outside the trial test runner.
        tmpdir_root = self.tmpdir.split(os.sep, 1)[0]
        shutil.rmtree(tmpdir_root)


class ServerTestCase(TrialTestCase):

    server = None

    def getDefaultServer(self):
        raise NotImplementedError("No default server")

    def installServer(self, server):
        self.server = server

    def setUpSignalHandling(self):
        self._oldSigChld = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def setUp(self):
        super(ServerTestCase, self).setUp()

        # Install the default SIGCHLD handler so that read() calls don't get
        # EINTR errors when child processes exit.
        self.setUpSignalHandling()

        if self.server is None:
            self.installServer(self.getDefaultServer())

        self.server.setUp()

    def tearDown(self):
        deferred1 = self.server.tearDown()
        signal.signal(signal.SIGCHLD, self._oldSigChld)
        deferred2 = defer.maybeDeferred(super(ServerTestCase, self).tearDown)
        return defer.gatherResults([deferred1, deferred2])

    def __str__(self):
        return self.id()

    def getTransport(self, relpath=None):
        return self.server.getTransport(relpath)


class BranchTestCase(TestCaseWithTransport):
    """Base class for tests that do a lot of things with branches."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self._integer = 0
        self.cursor = cursor()
        self.branch_set = getUtility(IBranchSet)

    def emptyPullQueues(self):
        transaction.begin()
        self.cursor.execute("UPDATE Branch SET mirror_request_time = NULL")
        transaction.commit()

    def getUniqueInteger(self):
        """Return an integer unique to this run of the test case."""
        self._integer += 1
        return self._integer

    def getUniqueString(self, prefix=None):
        """Return a string to this run of the test case.

        :param prefix: Used as a prefix for the unique string. If unspecified,
            defaults to the name of the test.
        """
        if prefix is None:
            prefix = self.id().split('.')[-1]
        return "%s%s" % (prefix, self.getUniqueInteger())

    def getUniqueURL(self):
        """Return a URL unique to this run of the test case."""
        return 'http://%s.example.com/%s' % (
            self.getUniqueString(), self.getUniqueString())

    def makePerson(self):
        """Create and return a new, arbitrary Person."""
        email = self.getUniqueString('email')
        name = self.getUniqueString('person-name')
        return getUtility(IPersonSet).createPersonAndEmail(
            email, rationale=PersonCreationRationale.UNKNOWN, name=name)[0]

    def makeProduct(self):
        """Create and return a new, arbitrary Product."""
        owner = self.makePerson()
        return getUtility(IProductSet).createProduct(
            owner, self.getUniqueString('product-name'),
            self.getUniqueString('displayname'),
            self.getUniqueString('title'),
            self.getUniqueString('summary'),
            self.getUniqueString('description'))

    def makeBranch(self, branch_type=None):
        """Create and return a new, arbitrary Branch of the given type."""
        if branch_type is None:
            branch_type = BranchType.HOSTED
        owner = self.makePerson()
        branch_name = self.getUniqueString('branch')
        product = self.makeProduct()
        if branch_type in (BranchType.HOSTED, BranchType.IMPORTED):
            url = None
        elif branch_type in (BranchType.MIRRORED, BranchType.REMOTE):
            url = self.getUniqueURL()
        else:
            raise UnknownBranchTypeError(
                'Unrecognized branch type: %r' % (branch_type,))
        return self.branch_set.new(
            branch_type, branch_name, owner, owner, product, url)

    def relaxSecurityPolicy(self):
        """Switch to using 'PermissiveSecurityPolicy'."""
        old_policy = getSecurityPolicy()
        setSecurityPolicy(PermissiveSecurityPolicy)
        self.addCleanup(lambda: setSecurityPolicy(old_policy))

    def restrictSecurityPolicy(self):
        """Switch to using 'LaunchpadSecurityPolicy'."""
        old_policy = getSecurityPolicy()
        setSecurityPolicy(LaunchpadSecurityPolicy)
        self.addCleanup(lambda: setSecurityPolicy(old_policy))


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
                    emailaddresses=['spiv@test.com'], wikiname='TestUser',
                    teams=[1, 2]),
            2: dict(name='testteam', displayname='Test Team', teams=[]),
            3: dict(name='name12', displayname='Other User',
                    emailaddresses=['test@test.com'], wikiname='OtherUser',
                    teams=[3]),
            }
        self._product_set = {
            1: dict(name='firefox'),
            2: dict(name='thunderbird'),
            }
        self._branch_set = {}
        self.createBranch(None, 'testuser', 'firefox', 'baz')
        self.createBranch(None, 'testuser', 'firefox', 'qux')
        self.createBranch(None, 'testuser', '+junk', 'random')
        self.createBranch(None, 'testteam', 'firefox', 'qux')
        self.createBranch(None, 'name12', '+junk', 'junk.dev')
        self._request_mirror_log = []

    def _lookup(self, item_set, item_id):
        row = dict(item_set[item_id])
        row['id'] = item_id
        return row

    def _insert(self, item_set, item_dict):
        new_id = max(item_set.keys() + [0]) + 1
        item_set[new_id] = item_dict
        return new_id

    def createBranch(self, login_id, user, product, branch_name):
        """See IHostedBranchStorage.createBranch."""
        for user_id, user_info in self._person_set.iteritems():
            if user_info['name'] == user:
                break
        else:
            return ''
        product_id = self.fetchProductID(product)
        if product_id is None:
            return ''
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

    def getBranchInformation(self, login_id, user_name, product_name,
                             branch_name):
        for branch_id, branch in self._branch_set.iteritems():
            owner = self._lookup(self._person_set, branch['user_id'])
            if branch['product_id'] == '':
                product = '+junk'
            else:
                product = self._product_set[branch['product_id']]['name']
            if ((owner['name'], product, branch['name'])
                == (user_name, product_name, branch_name)):
                logged_in_user = self._lookup(self._person_set, login_id)
                if owner['id'] in logged_in_user['teams']:
                    return branch_id, 'w'
                else:
                    return branch_id, 'r'
        return '', ''

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

    def requestMirror(self, branchID):
        self._request_mirror_log.append(branchID)


class CodeHostingTestProviderAdapter:
    """Test adapter to run a single test against many codehosting servers."""

    def __init__(self, servers):
        self._servers = servers

    def adaptForServer(self, test, serverFactory):
        from copy import deepcopy
        new_test = deepcopy(test)
        server = serverFactory()
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


def adapt_suite(adapter, base_suite):
    from bzrlib.tests import iter_suite_tests
    suite = unittest.TestSuite()
    for test in iter_suite_tests(base_suite):
        suite.addTests(adapter.adapt(test))
    return suite
