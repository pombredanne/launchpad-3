# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for codehosting tests."""

__metaclass__ = type
__all__ = [
    'AvatarTestCase', 'CodeHostingTestProviderAdapter',
    'CodeHostingRepositoryTestProviderAdapter', 'FakeLaunchpad',
    'ServerTestCase', 'adapt_suite', 'create_branch_with_one_revision',
    'deferToThread', 'make_bazaar_branch_and_tree']

import os
import shutil
import threading
import unittest

import transaction

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import FileExists, PermissionDenied, TransportNotPossible
from bzrlib.plugins.loom import branch as loom_branch
from bzrlib.tests import TestCaseWithTransport
from bzrlib.errors import SmartProtocolError

from zope.security.management import getSecurityPolicy, setSecurityPolicy

from canonical.authserver.interfaces import PERMISSION_DENIED_FAULT_CODE
from canonical.codehosting.transport import branch_id_to_path
from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing import LaunchpadFunctionalLayer, TwistedLayer

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata
from twisted.trial.unittest import TestCase as TrialTestCase
from twisted.web.xmlrpc import Fault


class AvatarTestCase(TrialTestCase):
    """Base class for tests that need a LaunchpadAvatar with some basic sample
    data.
    """

    layer = TwistedLayer

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
        # twisted.trial.unittest.TestCase.mktemp outside the trial test
        # runner.
        tmpdir_root = self.tmpdir.split(os.sep, 1)[0]
        shutil.rmtree(tmpdir_root)


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


class BranchTestCase(TestCaseWithTransport):
    """Base class for tests that do a lot of things with branches."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self._factory = LaunchpadObjectFactory()

    def createTemporaryBazaarBranchAndTree(self, base_directory='.'):
        """Create a local branch with one revision, return the working tree.
        """
        tree = self.make_branch_and_tree(base_directory)
        self.local_branch = tree.branch
        self.build_tree([os.path.join(base_directory, 'foo')])
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')
        return tree

    def emptyPullQueues(self):
        transaction.begin()
        cursor().execute("UPDATE Branch SET next_mirror_time = NULL")
        transaction.commit()

    def getUniqueInteger(self):
        """Return an integer unique to this run of the test case."""
        # Delegate to the factory.
        return self._factory.getUniqueInteger()

    def getUniqueString(self, prefix=None):
        """Return a string to this run of the test case.

        The string returned will always be a valid name that can be used in
        Launchpad URLs.

        :param prefix: Used as a prefix for the unique string. If unspecified,
            defaults to the name of the test.
        """
        if prefix is None:
            prefix = self.id().split('.')[-1]
        # Delegate to the factory.
        return self._factory.getUniqueString(prefix)

    def getUniqueURL(self):
        """Return a URL unique to this run of the test case."""
        # Delegate to the factory.
        return self._factory.getUniqueURL()

    def makePerson(self, email=None, name=None):
        """Create and return a new, arbitrary Person."""
        # Delegate to the factory.
        return self._factory.makePerson(email, name)

    def makeProduct(self):
        """Create and return a new, arbitrary Product."""
        # Delegate to the factory.
        return self._factory.makeProduct()

    def makeBranch(self, branch_type=None, owner=None, name=None,
                   product=None, url=None, **optional_branch_args):
        """Create and return a new, arbitrary Branch of the given type.

        Any parameters for IBranchSet.new can be specified to override the
        default ones.
        """
        # Delegate to the factory.
        return self._factory.makeBranch(
            branch_type, owner, name, product, url, **optional_branch_args)

    def restrictSecurityPolicy(self):
        """Switch to using 'LaunchpadSecurityPolicy'."""
        old_policy = getSecurityPolicy()
        setSecurityPolicy(LaunchpadSecurityPolicy)
        self.addCleanup(lambda: setSecurityPolicy(old_policy))

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


class ServerTestCase(TrialTestCase, BranchTestCase):

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

    def tearDown(self):
        deferred1 = self.server.tearDown()
        deferred2 = defer.maybeDeferred(super(ServerTestCase, self).tearDown)
        return defer.gatherResults([deferred1, deferred2])

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


class FakeLaunchpad:
    """Stub RPC interface to Launchpad.

    If the 'failing_branch_name' attribute is set and createBranch() is called
    with its value for the branch_name parameter, a Fault will be raised with
    code and message taken from the 'failing_branch_code' and
    'failing_branch_string' attributes respectively.
    """

    failing_branch_name = None
    failing_branch_code = None
    failing_branch_string = None

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

    def getDefaultStackedOnBranch(self, product_name):
        if product_name == '+junk':
            return ''
        elif product_name == 'evolution':
            # This has to match the sample data. :(
            return '~vcs-imports/evolution/main'
        elif product_name == 'firefox':
            return ''
        else:
            raise ValueError(
                "The crappy mock authserver doesn't know how to translate: %r"
                % (product_name,))

    def createBranch(self, login_id, user, product, branch_name):
        """See `IHostedBranchStorage.createBranch`.

        Also see the description of 'failing_branch_name' in the class
        docstring.
        """
        if self.failing_branch_name == branch_name:
            raise Fault(self.failing_branch_code, self.failing_branch_string)
        user_id = None
        for id, user_info in self._person_set.iteritems():
            if user_info['name'] == user:
                user_id = id
        if user_id is None:
            return ''
        product_id = self.fetchProductID(product)
        if product_id is None:
            return ''
        user = self.getUser(user_id)
        if product_id == '' and 'team' in user['name']:
            raise Fault(PERMISSION_DENIED_FAULT_CODE,
                        'Cannot create team-owned +junk branches.')
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

    def requestMirror(self, loginID, branchID):
        self._request_mirror_log.append((loginID, branchID))


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
