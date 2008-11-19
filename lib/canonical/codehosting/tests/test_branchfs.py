# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Tests for the branch filesystem."""

__metaclass__ = type

import os
import unittest

from bzrlib import errors
from bzrlib.bzrdir import BzrDir
from bzrlib.tests import (
    TestCase as BzrTestCase, TestCaseInTempDir, TestCaseWithTransport)
from bzrlib.transport import (
    get_transport, _get_protocol_handlers, register_transport, Server,
    unregister_transport)
from bzrlib.transport.memory import MemoryServer, MemoryTransport
from bzrlib.urlutils import escape, local_path_to_url

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfs import (
    AsyncLaunchpadTransport, InvalidControlDirectory, LaunchpadInternalServer,
    LaunchpadServer, make_control_transport)
from canonical.codehosting.branchfsclient import BlockingProxy
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from canonical.codehosting.sftp import FatLocalTransport
from canonical.codehosting.transport import AsyncVirtualTransport
from canonical.launchpad.interfaces.branch import BranchType
from canonical.launchpad.testing import TestCase
from canonical.testing import TwistedLayer


def branch_to_path(branch, add_slash=True):
    path = branch_id_to_path(branch.id)
    if add_slash:
        path += '/'
    return path


class TestControlTransport(TestCase):
    """Tests for the control transport factory."""

    def test_control_conf_read_only(self):
        transport = make_control_transport(
            default_stack_on='/~foo/bar/baz')
        self.assertRaises(
            errors.TransportNotPossible,
            transport.put_bytes, '.bzr/control.conf', 'data')

    def test_control_conf_with_stacking(self):
        transport = make_control_transport(
            default_stack_on='/~foo/bar/baz')
        control_conf = transport.get_bytes('.bzr/control.conf')
        self.assertEqual('default_stack_on = /~foo/bar/baz\n', control_conf)

    def test_control_conf_with_no_stacking(self):
        transport = make_control_transport('')
        self.assertEqual([], transport.list_dir('.'))


class TestBranchIDToPath(unittest.TestCase):
    """Tests for branch_id_to_path."""

    def test_branch_id_to_path(self):
        # branch_id_to_path converts an integer branch ID into a path of four
        # segments, with each segment being a hexadecimal number.
        self.assertEqual('00/00/00/00', branch_id_to_path(0))
        self.assertEqual('00/00/00/01', branch_id_to_path(1))
        arbitrary_large_id = 6731
        assert "%x" % arbitrary_large_id == '1a4b', (
            "The arbitrary large id is not what we expect (1a4b): %s"
            % (arbitrary_large_id))
        self.assertEqual('00/00/1a/4b', branch_id_to_path(6731))


class MixinBaseLaunchpadServerTests:
    """Common tests for _BaseLaunchpadServer subclasses."""

    layer = TwistedLayer

    def setUp(self):
        frontend = InMemoryFrontend()
        self.authserver = frontend.getFilesystemEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.requester = self.factory.makePerson()
        self.server = self.getLaunchpadServer(
            self.authserver, self.requester.id)

    def getLaunchpadServer(self, authserver, user_id):
        raise NotImplementedError(
            "Override this with a Launchpad server factory.")

    def test_setUp(self):
        # Setting up the server registers its schema with the protocol
        # handlers.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertTrue(
            self.server.get_url() in _get_protocol_handlers().keys())

    def test_tearDown(self):
        # Setting up then tearing down the server removes its schema from the
        # protocol handlers.
        self.server.setUp()
        self.server.tearDown()
        self.assertFalse(
            self.server.get_url() in _get_protocol_handlers().keys())


class TestLaunchpadServer(MixinBaseLaunchpadServerTests, TrialTestCase,
                          BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)
        MixinBaseLaunchpadServerTests.setUp(self)

    def getLaunchpadServer(self, authserver, user_id):
        return LaunchpadServer(
            BlockingProxy(authserver), user_id, MemoryTransport(),
            MemoryTransport())

    def test_translateControlPath(self):
        branch = self.factory.makeBranch(owner=self.requester)
        branch.product.development_focus.user_branch = branch
        deferred = self.server.translateVirtualPath(
            '~%s/%s/.bzr/control.conf'
            % (branch.owner.name, branch.product.name))
        def check_control_file((transport, path)):
            self.assertEqual(
                'default_stack_on = /%s\n' % branch.unique_name,
                transport.get_bytes(path))
        return deferred.addCallback(check_control_file)

    def test_base_path_translation_person_branch(self):
        # Branches are stored on the filesystem by branch ID. This allows
        # users to rename and re-assign branches without causing unnecessary
        # disk churn. The ID is converted to four-byte hexadecimal and split
        # into four path segments, to make sure that the directory tree
        # doesn't get too wide and cause ext3 to have conniptions.
        #
        # However, branches are _accessed_ using their
        # ~person/product/branch-name. The server knows how to map this unique
        # name to the branch's path on the filesystem.

        # We can map a branch owned by the user to its path.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._hosted_transport, branch_to_path(branch)))
        return deferred

    def test_base_path_translation_junk_branch(self):
        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester, product=None)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._hosted_transport, branch_to_path(branch)))
        return deferred

    def test_base_path_translation_team_branch(self):
        # We can map a branch owned by a team that the user is in to its path.
        team = self.factory.makeTeam(self.requester)
        branch = self.factory.makeBranch(BranchType.HOSTED, owner=team)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._hosted_transport, branch_to_path(branch)))
        return deferred

    def test_base_path_translation_other_junk_branch(self):
        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        branch = self.factory.makeBranch(BranchType.HOSTED, product=None)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._mirror_transport, branch_to_path(branch)))
        return deferred

    def test_extend_path_translation_on_mirror(self):
        branch = self.factory.makeBranch(BranchType.HOSTED, product=None)
        deferred = self.server.translateVirtualPath(
            '/%s/.bzr' % branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._mirror_transport,
             '%s/.bzr' % branch_id_to_path(branch.id)))
        return deferred

    def test_extend_path_translation_on_hosted(self):
        # More than just the branch name needs to be translated: transports
        # will ask for files beneath the branch. The server translates the
        # unique name of the branch (i.e. the ~user/product/branch-name part)
        # to the four-byte hexadecimal split ID described in
        # test_base_path_translation and appends the remainder of the path.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        deferred = self.server.translateVirtualPath(
            '/%s/.bzr' % branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._hosted_transport,
             '%s/.bzr' % branch_id_to_path(branch.id)))
        return deferred

    def test_get_url(self):
        # The URL of the server is 'lp-<number>:///', where <number> is the
        # id() of the server object. Including the id allows for multiple
        # Launchpad servers to be running within a single process.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())

    def test_buildControlDirectory(self):
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

        branch = 'http://example.com/~user/product/branch'
        transport = self.server._buildControlDirectory(branch)
        self.assertEqual(
            'default_stack_on = %s\n' % branch,
            transport.get_bytes('.bzr/control.conf'))

    def test_buildControlDirectory_no_branch(self):
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

        transport = self.server._buildControlDirectory('')
        self.assertEqual([], transport.list_dir('.'))

    def test_parseProductControlDirectory(self):
        # _parseProductControlDirectory takes a path to a product control
        # directory and returns the name of the product, followed by the path.
        product, path = self.server._parseProductControlDirectory(
            '~user/product/.bzr')
        self.assertEqual('product', product)
        self.assertEqual('.bzr', path)
        product, path = self.server._parseProductControlDirectory(
            '~user/product/.bzr/foo')
        self.assertEqual('product', product)
        self.assertEqual('.bzr/foo', path)

    def test_parseProductControlDirectoryNotControlDir(self):
        # If the directory isn't a control directory (doesn't have '.bzr'),
        # raise an error.
        self.assertRaises(
            InvalidControlDirectory,
            self.server._parseProductControlDirectory,
            '~user/product/branch')

    def test_parseProductControlDirectoryTooShort(self):
        # If there aren't enough path segments, raise an error.
        self.assertRaises(
            InvalidControlDirectory,
            self.server._parseProductControlDirectory,
            '~user')
        self.assertRaises(
            InvalidControlDirectory,
            self.server._parseProductControlDirectory,
            '~user/product')

    def test_parseProductControlDirectoryInvalidUser(self):
        # If the user directory is invalid, raise an InvalidControlDirectory.
        self.assertRaises(
            InvalidControlDirectory,
            self.server._parseProductControlDirectory,
            'user/product/.bzr/foo')


class TestLaunchpadInternalServer(MixinBaseLaunchpadServerTests,
                                  TrialTestCase, BzrTestCase):
    """Tests for the LaunchpadInternalServer, used by the puller and scanner.
    """

    def setUp(self):
        BzrTestCase.setUp(self)
        MixinBaseLaunchpadServerTests.setUp(self)

    def getLaunchpadServer(self, authserver, user_id):
        return LaunchpadInternalServer(
            'lp-test:///', XMLRPCWrapper(authserver), MemoryTransport())

    def test_base_path_translation_person_branch(self):
        # Branches are stored on the filesystem by branch ID. This allows
        # users to rename and re-assign branches without causing unnecessary
        # disk churn. The ID is converted to four-byte hexadecimal and split
        # into four path segments, to make sure that the directory tree
        # doesn't get too wide and cause ext3 to have conniptions.
        #
        # However, branches are _accessed_ using their
        # ~person/product/branch-name. The server knows how to map this unique
        # name to the branch's path on the filesystem.

        branch = self.factory.makeBranch(owner=self.requester)
        # We can map a branch owned by the user to its path.
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._branch_transport, branch_to_path(branch)))
        return deferred

    def test_base_path_translation_junk_branch(self):
        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        branch = self.factory.makeBranch(owner=self.requester, product=None)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._branch_transport, branch_to_path(branch)))
        return deferred

    def test_base_path_translation_team_branch(self):
        # We can map a branch owned by a team that the user is in to its path.
        team = self.factory.makeTeam(self.requester)
        branch = self.factory.makeBranch(BranchType.HOSTED, owner=team)
        deferred = self.server.translateVirtualPath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (self.server._branch_transport, branch_to_path(branch)))
        return deferred

    def test_open_containing_raises_branch_not_found(self):
        # open_containing_from_transport raises NotBranchError if there's no
        # branch at that URL.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        branch = self.factory.makeBranch(owner=self.requester)
        transport = get_transport(self.server.get_url())
        transport = transport.clone(branch.unique_name)
        self.assertRaises(
            errors.NotBranchError,
            BzrDir.open_containing_from_transport, transport)


class TestAsyncVirtualTransport(TrialTestCase, TestCaseInTempDir):
    """Tests for `AsyncVirtualTransport`."""

    layer = TwistedLayer

    class VirtualServer(Server):
        """Very simple server that provides a AsyncVirtualTransport."""

        def __init__(self, backing_transport):
            self._branch_transport = backing_transport

        def _transportFactory(self, url):
            return AsyncVirtualTransport(self, url)

        def get_url(self):
            return self.scheme

        def setUp(self):
            self.scheme = 'virtual:///'
            register_transport(self.scheme, self._transportFactory)

        def tearDown(self):
            unregister_transport(self.scheme, self._transportFactory)

        def translateVirtualPath(self, virtual_path):
            return defer.succeed(
                (self._branch_transport,
                 'prefix_' + virtual_path.lstrip('/')))

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.server = self.VirtualServer(
            FatLocalTransport(local_path_to_url('.')))
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.transport = get_transport(self.server.get_url())

    def test_writeChunk(self):
        deferred = self.transport.writeChunk('foo', 0, 'content')
        return deferred.addCallback(
            lambda ignored:
            self.assertEqual('content', open('prefix_foo').read()))

    def test_realPath(self):
        # local_realPath returns the real, absolute path to a file, resolving
        # any symlinks.
        deferred = self.transport.mkdir('baz')

        def symlink_and_clone(ignored):
            os.symlink('prefix_foo', 'prefix_baz/bar')
            return self.transport.clone('baz')

        def get_real_path(transport):
            return transport.local_realPath('bar')

        def check_real_path(real_path):
            self.assertEqual('/baz/bar', real_path)

        deferred.addCallback(symlink_and_clone)
        deferred.addCallback(get_real_path)
        return deferred.addCallback(check_real_path)

    def test_realPathEscaping(self):
        # local_realPath returns an escaped path to the file.
        escaped_path = escape('~baz')
        deferred = self.transport.mkdir(escaped_path)

        def get_real_path(ignored):
            return self.transport.local_realPath(escaped_path)

        deferred.addCallback(get_real_path)
        return deferred.addCallback(self.assertEqual, '/' + escaped_path)

    def test_canAccessEscapedPathsOnDisk(self):
        # Sometimes, the paths to files on disk are themselves URL-escaped.
        # The AsyncVirtualTransport can access these files.
        #
        # This test added in response to https://launchpad.net/bugs/236380.
        escaped_disk_path = 'prefix_%43razy'
        content = 'content\n'
        escaped_file = open(escaped_disk_path, 'w')
        escaped_file.write(content)
        escaped_file.close()

        deferred = self.transport.get_bytes(escape('%43razy'))
        return deferred.addCallback(self.assertEqual, content)


class LaunchpadTransportTests:
    """Tests for a Launchpad transport.

    These tests are expected to run against two kinds of transport.
      1. An asynchronous one that returns Deferreds.
      2. A synchronous one that returns actual values.

    To support that, subclasses must implement `getTransport` and
    `_ensureDeferred`. See these methods for more information.
    """

    # See comment on TestLaunchpadServer.
    layer = TwistedLayer

    def setUp(self):
        frontend = InMemoryFrontend()
        self.factory = frontend.getLaunchpadObjectFactory()
        authserver = frontend.getFilesystemEndpoint()
        self.requester = self.factory.makePerson()
        self.backing_transport = MemoryTransport()
        self.server = self.getServer(
            authserver, self.requester.id, self.backing_transport,
            MemoryTransport())
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

    def assertFiresFailure(self, exception, function, *args, **kwargs):
        """Assert that calling `function` will cause `exception` to be fired.

        In the synchronous tests, this means that `function` raises
        `exception`. In the asynchronous tests, `function` returns a Deferred
        that fires `exception` as a Failure.

        :return: A `Deferred`. You must return this from your test.
        """
        return self.assertFailure(
            self._ensureDeferred(function, *args, **kwargs), exception)

    def assertFiresFailureWithSubstring(self, exc_type, msg, function,
                                        *args, **kw):
        """Assert that calling function(*args, **kw) fails in a certain way.

        This method is like assertFiresFailure() but in addition checks that
        'msg' is a substring of the str() of the raised exception.
        """
        deferred = self.assertFiresFailure(exc_type, function, *args, **kw)
        return deferred.addCallback(
            lambda exception: self.assertIn(msg, str(exception)))

    def _ensureDeferred(self, function, *args, **kwargs):
        """Call `function` and return an appropriate Deferred."""
        raise NotImplementedError

    def getServer(self, authserver, user_id, backing_transport,
                  mirror_transport):
        return LaunchpadServer(
            XMLRPCWrapper(authserver), user_id, backing_transport,
            mirror_transport)

    def getTransport(self):
        """Return the transport to be tested."""
        raise NotImplementedError()

    def test_get_transport(self):
        # When the server is set up, getting a transport for the server URL
        # returns a LaunchpadTransport pointing at that URL. That is, the
        # transport is registered once the server is set up.
        transport = self.getTransport()
        self.assertEqual(self.server.get_url(), transport.base)

    def test_cant_write_to_control_conf(self):
        # You can't write to the control.conf file if it exists. It's
        # generated by Launchpad based on info in the database, rather than
        # being an actual file on disk.
        transport = self.getTransport()
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        branch.product.development_focus.user_branch = branch
        return self.assertFiresFailure(
            errors.TransportNotPossible,
            transport.put_bytes,
            '~%s/%s/.bzr/control.conf' % (
                branch.owner.name, branch.product.name),
            'hello nurse!')

    def _makeOnBackingTransport(self, branch):
        """Make directories for 'branch' on the backing transport.

        :return: a transport for the .bzr directory of 'branch'.
        """
        backing_transport = self.backing_transport.clone(
            '%s/.bzr/' % branch_to_path(branch, add_slash=False))
        ensure_base(backing_transport)
        return backing_transport

    def test_get_mapped_file(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport.
        transport = self.getTransport()
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        deferred = self._ensureDeferred(
            transport.get_bytes, '%s/.bzr/hello.txt' % branch.unique_name)
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_get_mapped_file_escaped_url(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport, even when the URL is escaped.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        url = escape('%s/.bzr/hello.txt' % branch.unique_name)
        transport = self.getTransport()
        deferred = self._ensureDeferred(transport.get_bytes, url)
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_readv_mapped_file(self):
        # Using readv on a public branch URL gets chunks of the file as stored
        # on the base transport.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        data = 'Hello World!'
        backing_transport.put_bytes('hello.txt', data)
        transport = self.getTransport()
        deferred = self._ensureDeferred(
            transport.readv, '%s/.bzr/hello.txt' % branch.unique_name,
            [(3, 2)])
        def get_chunk(generator):
            return generator.next()[1]
        deferred.addCallback(get_chunk)
        return deferred.addCallback(self.assertEqual, data[3:5])

    def test_put_mapped_file(self):
        # Putting a file from a public branch URL stores the file in the
        # mapped URL on the base transport.
        transport = self.getTransport()
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        deferred = self._ensureDeferred(
            transport.put_bytes,
            '%s/.bzr/goodbye.txt' % branch.unique_name, "Goodbye")
        def check_bytes_written(ignored):
            self.assertEqual(
                "Goodbye", backing_transport.get_bytes('goodbye.txt'))
        return deferred.addCallback(check_bytes_written)

    def test_cloning_updates_base(self):
        # A transport can be constructed using a path relative to another
        # transport by using 'clone'. When this happens, it's necessary for
        # the newly constructed transport to preserve the non-relative path
        # information from the transport being cloned. It's necessary because
        # the transport needs to have the '~user/product/branch-name' in order
        # to translate paths.
        transport = self.getTransport()
        self.assertEqual(self.server.get_url(), transport.base)
        transport = transport.clone('~testuser')
        self.assertEqual(self.server.get_url() + '~testuser', transport.base)

    def test_abspath_without_schema(self):
        # _abspath returns the absolute path for a given relative path, but
        # without the schema part of the URL that is included by abspath.
        transport = self.getTransport()
        self.assertEqual(
            '/~testuser/firefox/baz',
            transport._abspath('~testuser/firefox/baz'))
        transport = transport.clone('~testuser')
        self.assertEqual(
            '/~testuser/firefox/baz', transport._abspath('firefox/baz'))

    def test_cloning_preserves_path_mapping(self):
        # The public branch URL -> filesystem mapping uses the base URL to do
        # its mapping, thus ensuring that clones map correctly.
        transport = self.getTransport()
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        transport = transport.clone('~%s' % branch.owner.name)
        deferred = self._ensureDeferred(
            transport.get_bytes,
            '%s/%s/.bzr/hello.txt' % (branch.product.name, branch.name))
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_abspath(self):
        # abspath for a relative path is the same as the base URL for a clone
        # for that relative path.
        transport = self.getTransport()
        self.assertEqual(
            transport.clone('~testuser').base, transport.abspath('~testuser'))

    def test_incomplete_path_not_found(self):
        # For a branch URL to be complete, it needs to have a person, product
        # and branch. Trying to perform operations on an incomplete URL raises
        # an error. Which kind of error is not particularly important.
        transport = self.getTransport()
        return self.assertFiresFailure(
            errors.NoSuchFile, transport.get, '~testuser')

    def test_complete_non_existent_path_not_found(self):
        # Bazaar looks for files inside a branch directory before it looks for
        # the branch itself. If the branch doesn't exist, any files it asks
        # for are not found. i.e. we raise NoSuchFile
        transport = self.getTransport()
        return self.assertFiresFailure(
            errors.NoSuchFile,
            transport.get, '~testuser/firefox/new-branch/.bzr/branch-format')

    def test_rename(self):
        # We can use the transport to rename files where both the source and
        # target are virtual paths.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')

        transport = self.getTransport().clone(branch.unique_name)

        deferred = self._ensureDeferred(transport.list_dir, '.bzr')
        deferred.addCallback(set)

        def rename_file(dir_contents):
            """Rename a file and return the original directory contents."""
            deferred = self._ensureDeferred(
                transport.rename, '.bzr/hello.txt', '.bzr/goodbye.txt')
            deferred.addCallback(lambda ignored: dir_contents)
            return deferred

        def check_file_was_renamed(dir_contents):
            """Check that the old name isn't there and the new name is."""
            # Replace the old name with the new name.
            dir_contents.remove('hello.txt')
            dir_contents.add('goodbye.txt')
            deferred = self._ensureDeferred(transport.list_dir, '.bzr')
            deferred.addCallback(set)
            # Check against the virtual transport.
            deferred.addCallback(self.assertEqual, dir_contents)
            # Check against the backing transport.
            deferred.addCallback(
                lambda ignored:
                self.assertEqual(
                    set(backing_transport.list_dir('.')), dir_contents))
            return deferred
        deferred.addCallback(rename_file)
        return deferred.addCallback(check_file_was_renamed)

    def test_iter_files_recursive(self):
        # iter_files_recursive doesn't take a relative path but still needs to
        # do a path-based operation on the backing transport, so the
        # implementation can't just be a shim to the backing transport.
        branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        transport = self.getTransport().clone(branch.unique_name)
        backing_transport = self.backing_transport.clone(
            branch_to_path(branch))
        deferred = self._ensureDeferred(transport.iter_files_recursive)

        def check_iter_result(iter_files, expected_files):
            self.assertEqual(expected_files, list(iter_files))

        deferred.addCallback(
            check_iter_result,
            list(backing_transport.iter_files_recursive()))
        return deferred

    def test_make_two_directories(self):
        # Bazaar doesn't have a makedirs() facility for transports, so we need
        # to make sure that we can make a directory on the backing transport
        # if its parents exist and if they don't exist.
        product = self.factory.makeProduct()
        banana = '~%s/%s/banana' % (self.requester.name, product.name)
        orange = '~%s/%s/orange' % (self.requester.name, product.name)
        transport = self.getTransport()
        transport.mkdir(banana)
        transport.mkdir(orange)
        self.assertTrue(transport.has(banana))
        self.assertTrue(transport.has(orange))

    def test_createBranch_not_found_error(self):
        # When createBranch raises an exception with faultCode
        # NOT_FOUND_FAULT_CODE, the transport should translate this to a
        # TransportNotPossible exception (see the comment in transport.py for
        # why we translate to TransportNotPossible and not NoSuchFile).
        transport = self.getTransport()
        return self.assertFiresFailureWithSubstring(
            errors.PermissionDenied, "does not exist", transport.mkdir,
            '~%s/no-such-product/some-name' % self.requester.name)

    def test_createBranch_permission_denied_error(self):
        # When createBranch raises an exception with faultCode
        # PERMISSION_DENIED_FAULT_CODE, the transport should translate
        # this to a PermissionDenied exception.
        transport = self.getTransport()
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        message = (
            "%s cannot create branches owned by %s"
            % (self.requester.displayname, person.displayname))
        return self.assertFiresFailureWithSubstring(
            errors.PermissionDenied, message,
            transport.mkdir, '~%s/%s/some-name' % (person.name, product.name))

    def test_rmdir(self):
        transport = self.getTransport()
        self.assertFiresFailure(
            errors.PermissionDenied,
            transport.rmdir, '~testuser/firefox/baz')


class TestLaunchpadTransportSync(LaunchpadTransportTests, TrialTestCase):

    def _ensureDeferred(self, function, *args, **kwargs):
        def call_function_and_check_not_deferred():
            ret = function(*args, **kwargs)
            self.assertFalse(
                isinstance(ret, defer.Deferred),
                "%r returned a Deferred." % (function,))
            return ret
        return defer.maybeDeferred(call_function_and_check_not_deferred)

    def setUp(self):
        TrialTestCase.setUp(self)
        LaunchpadTransportTests.setUp(self)

    def getTransport(self):
        return get_transport(self.server.get_url())

    def test_ensureDeferredFailsWhenDeferredReturned(self):
        return self.assertFailure(
            self._ensureDeferred(defer.succeed, None), AssertionError)


class TestLaunchpadTransportAsync(LaunchpadTransportTests, TrialTestCase):

    def _ensureDeferred(self, function, *args, **kwargs):
        deferred = function(*args, **kwargs)
        self.assertIsInstance(deferred, defer.Deferred)
        return deferred

    def setUp(self):
        TrialTestCase.setUp(self)
        LaunchpadTransportTests.setUp(self)

    def getTransport(self):
        url = self.server.get_url()
        return AsyncLaunchpadTransport(self.server, url)


class TestRequestMirror(TestCaseWithTransport):
    """Test request mirror behaviour."""

    def setUp(self):
        self._server = None
        self._request_mirror_log = []
        frontend = InMemoryFrontend()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.authserver = frontend.getFilesystemEndpoint()
        self.authserver.requestMirror = (
            lambda *args: self._request_mirror_log.append(args))
        self.requester = self.factory.makePerson()
        self.backing_transport = MemoryTransport()
        self.mirror_transport = MemoryTransport()

    def get_server(self):
        if self._server is None:
            self._server = LaunchpadServer(
                BlockingProxy(self.authserver), self.requester.id,
                self.backing_transport, self.mirror_transport)
            self._server.setUp()
            self.addCleanup(self._server.tearDown)
        return self._server

    def test_no_mirrors_requested_if_no_branches_changed(self):
        self.assertEqual([], self._request_mirror_log)

    def test_creating_branch_requests_mirror(self):
        # Creating a branch requests a mirror.
        db_branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        branch = self.make_branch(db_branch.unique_name)
        self.assertEqual(
            [(self.requester.id, db_branch.id)], self._request_mirror_log)

    def test_branch_unlock_requests_mirror(self):
        # Unlocking a branch requests a mirror.
        db_branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester)
        branch = self.make_branch(db_branch.unique_name)
        self._request_mirror_log = []
        branch.lock_write()
        branch.unlock()
        self.assertEqual(
            [(self.requester.id, db_branch.id)], self._request_mirror_log)


class TestLaunchpadTransportReadOnly(TrialTestCase, BzrTestCase):
    """Tests for read-only operations on the LaunchpadTransport."""

    # See comment on TestLaunchpadServer.
    layer = TwistedLayer

    def setUp(self):
        BzrTestCase.setUp(self)

        memory_server = self._setUpMemoryServer()
        memory_transport = get_transport(memory_server.get_url())
        backing_transport = memory_transport.clone('backing')
        mirror_transport = memory_transport.clone('mirror')

        self._frontend = InMemoryFrontend()
        self.factory = self._frontend.getLaunchpadObjectFactory()

        authserver = self._frontend.getFilesystemEndpoint()
        self.requester = self.factory.makePerson()

        self.writable_branch = self.factory.makeBranch(
            BranchType.HOSTED, owner=self.requester).unique_name
        self.read_only_branch = self.factory.makeBranch(
            BranchType.HOSTED).unique_name

        self.lp_server = self._setUpLaunchpadServer(
            self.requester.id, authserver, backing_transport,
            mirror_transport)
        self.lp_transport = get_transport(self.lp_server.get_url())

        self.writable_file = '/%s/.bzr/hello.txt' % self.writable_branch
        self.file_on_both_transports = '/%s/.bzr/README' % (
            self.read_only_branch,)
        self.file_on_mirror_only = '/%s/.bzr/MIRROR-ONLY' % (
            self.read_only_branch,)

        d1 = self._makeFilesInBranches(
            backing_transport,
            [(self.writable_file, 'Hello World!'),
             (self.file_on_both_transports, 'Hello World!')])

        d2 = self._makeFilesInBranches(
            mirror_transport,
            [(self.file_on_both_transports, 'Goodbye World!'),
             (self.file_on_mirror_only, 'ignored')])

        return defer.gatherResults([d1, d2])

    def _setUpMemoryServer(self):
        memory_server = MemoryServer()
        memory_server.setUp()
        self.addCleanup(memory_server.tearDown)
        return memory_server

    def _setUpLaunchpadServer(self, user_id, authserver, backing_transport,
                              mirror_transport):
        server = LaunchpadServer(
            BlockingProxy(authserver), user_id, backing_transport,
            mirror_transport)
        server.setUp()
        self.addCleanup(server.tearDown)
        return server

    def _makeFilesInBranches(self, transport, file_spec):
        """Write a bunch of files inside branches on the LP codehost.

        :param transport: Either a backing transport or a mirror transport
            for a Launchpad server.
        :param file_spec: A list of (filename, contents) tuples.
            The path in the filename is translated as if it were a virtual
            path.
        """

        def make_file(filename, contents):
            deferred = self.lp_server.translateVirtualPath(filename)
            def write_to_file(branch_info):
                path_to_file = branch_info[1]
                directory = os.path.dirname(path_to_file)
                ensure_base(transport.clone(directory))
                transport.put_bytes(path_to_file, contents)
            return deferred.addCallback(write_to_file)
        return defer.gatherResults(
            [make_file(filename, contents)
             for filename, contents in file_spec])

    def test_mkdir_readonly(self):
        # If we only have READ_ONLY access to a branch then we should not be
        # able to create directories within that branch.
        self.assertRaises(
            errors.TransportNotPossible,
            self.lp_transport.mkdir, '%s/.bzr' % self.read_only_branch)

    def test_rename_target_readonly(self):
        # Even if we can write to a file, we can't rename it to location which
        # is read-only to us.
        self.assertRaises(
            errors.TransportNotPossible,
            self.lp_transport.rename, self.writable_file,
            '/%s/.bzr/goodbye.txt' % self.read_only_branch)

    def test_readonly_refers_to_mirror(self):
        # Read-only operations should get their data from the mirror, not the
        # primary backing transport.
        # XXX: JonathanLange 2007-06-21, Explain more of this.
        self.assertEqual(
            'Goodbye World!',
            self.lp_transport.get_bytes(self.file_on_both_transports))

    def test_iter_files_refers_to_mirror(self):
        # iter_files_recursive() gets its data from the mirror if it cannot
        # write to the branch.
        read_only_branch_name = '/%s/' % self.read_only_branch
        transport = self.lp_transport.clone(read_only_branch_name)
        files = list(transport.iter_files_recursive())

        mirror_only = self.file_on_mirror_only[len(read_only_branch_name):]
        self.assertTrue(
            mirror_only in files, '%r not in %r' % (mirror_only, files))

    def test_listable_refers_to_mirror(self):
        # listable() refers to the mirror transport for read-only branches.
        read_only_branch_name = '/%s' % self.read_only_branch
        transport = self.lp_transport.clone(read_only_branch_name)

        # listable() returns the same value for both transports. To
        # distinguish them, we'll monkey patch the mirror and backing
        # transports.
        self.lp_server._mirror_transport.listable = lambda: 'mirror'
        self.lp_server._hosted_transport.listable = lambda: 'hosted'
        self.assertEqual('mirror', transport.listable())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

