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

from canonical.codehosting.vfs.branchfs import (
    AsyncLaunchpadTransport, branch_id_to_path, LaunchpadInternalServer,
    LaunchpadServer, BranchTransportDispatch, TransportDispatch,
    UnknownTransportType)
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from canonical.codehosting.sftp import FatLocalTransport
from canonical.codehosting.vfs.transport import AsyncVirtualTransport
from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.codehosting import (
    BRANCH_TRANSPORT, CONTROL_TRANSPORT)
from canonical.launchpad.testing import TestCase
from canonical.testing import TwistedLayer


def branch_to_path(branch, add_slash=True):
    path = branch_id_to_path(branch.id)
    if add_slash:
        path += '/'
    return path


class TestBranchTransportDispatch(TestCase):

    def setUp(self):
        super(TestBranchTransportDispatch, self).setUp()
        memory_server = MemoryServer()
        memory_server.setUp()
        self.base_transport = get_transport(memory_server.get_url())
        self.factory = BranchTransportDispatch(self.base_transport)

    def test_writable_false_ignored(self):
        transport, path = self.factory.makeTransport(
            (BRANCH_TRANSPORT, dict(id=5, writable=False), ''))
        transport.mkdir('.bzr')
        self.assertEqual(['.bzr'], transport.list_dir('.'))

    def test_writable_implies_writable(self):
        transport, path = self.factory.makeTransport(
            (BRANCH_TRANSPORT, dict(id=5, writable=True), ''))
        transport.mkdir('.bzr')
        self.assertEqual(['.bzr'], transport.list_dir('.'))

    def test_gets_id_directory(self):
        transport, path = self.factory.makeTransport(
            (BRANCH_TRANSPORT, dict(id=5, writable=True), ''))
        transport.mkdir('.bzr')
        self.assertEqual(
            ['.bzr'], self.base_transport.list_dir('00/00/00/05'))

    def test_returns_trailing_path(self):
        transport, path = self.factory.makeTransport(
            (BRANCH_TRANSPORT, dict(id=5, writable=True), '.bzr/foo'))
        self.assertEqual('.bzr/foo', path)

    def test_makeTransport_control(self):
        # makeTransport raises UnknownTransportType for the control transport.
        self.assertRaises(
            UnknownTransportType, self.factory.makeTransport,
            (CONTROL_TRANSPORT, {}, ''))


class TestTransportDispatch(TestCase):
    """Tests for the transport factory."""

    def setUp(self):
        super(TestTransportDispatch, self).setUp()
        memory_server = MemoryServer()
        memory_server.setUp()
        base_transport = get_transport(memory_server.get_url())
        base_transport.mkdir('hosted')
        base_transport.mkdir('mirrored')
        self.hosted_transport = base_transport.clone('hosted')
        self.mirrored_transport = base_transport.clone('mirrored')
        self.factory = TransportDispatch(
            self.hosted_transport, self.mirrored_transport)

    def test_control_conf_read_only(self):
        transport = self.factory._makeControlTransport(
            default_stack_on='/~foo/bar/baz')
        self.assertRaises(
            errors.TransportNotPossible,
            transport.put_bytes, '.bzr/control.conf', 'data')

    def test_control_conf_with_stacking(self):
        transport = self.factory._makeControlTransport(
            default_stack_on='/~foo/bar/baz')
        control_conf = transport.get_bytes('.bzr/control.conf')
        self.assertEqual('default_stack_on = /~foo/bar/baz\n', control_conf)

    def test_control_conf_with_no_stacking(self):
        transport = self.factory._makeControlTransport(
            default_stack_on='')
        self.assertEqual([], transport.list_dir('.'))

    def test_writable_false_implies_readonly(self):
        transport = self.factory._makeBranchTransport(id=5, writable=False)
        self.assertRaises(
            errors.TransportNotPossible, transport.put_bytes,
            '.bzr/README', 'data')

    def test_writable_implies_writable(self):
        transport = self.factory._makeBranchTransport(id=5, writable=True)
        transport.mkdir('.bzr')
        self.assertEqual(['.bzr'], transport.list_dir('.'))

    def test_gets_id_directory(self):
        transport = self.factory._makeBranchTransport(id=5, writable=True)
        transport.mkdir('.bzr')
        self.assertEqual(
            ['.bzr'], self.hosted_transport.list_dir('00/00/00/05'))

    def test_read_only_returns_mirrored(self):
        self.mirrored_transport.mkdir_multi(
            ['00', '00/00', '00/00/00', '00/00/00/05', '00/00/00/05/.bzr'])
        self.mirrored_transport.put_bytes('00/00/00/05/.bzr/README', "Hello")
        transport = self.factory._makeBranchTransport(id=5, writable=False)
        data = transport.get_bytes(".bzr/README")
        self.assertEqual("Hello", data)

    def test_makeTransport_control(self):
        # makeTransport returns a control transport for the tuple.
        log = []
        self.factory._transport_factories[CONTROL_TRANSPORT] = (
            lambda default_stack_on, trailing_path:
                log.append(default_stack_on))
        transport, path = self.factory.makeTransport(
            (CONTROL_TRANSPORT, {'default_stack_on': 'foo'}, 'bar/baz'))
        self.assertEqual('bar/baz', path)
        self.assertEqual(['foo'], log)

    def test_makeTransport_branch(self):
        # makeTransport returns a control transport for the tuple.
        log = []
        self.factory._transport_factories[BRANCH_TRANSPORT] = (
            lambda id, writable, trailing_path: log.append((id, writable)))
        transport, path = self.factory.makeTransport(
            (BRANCH_TRANSPORT, {'id': 1, 'writable': True}, 'bar/baz'))
        self.assertEqual('bar/baz', path)
        self.assertEqual([(1, True)], log)


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
            XMLRPCWrapper(authserver), user_id, MemoryTransport(),
            MemoryTransport())

    def test_translateControlPath(self):
        branch = self.factory.makeProductBranch(owner=self.requester)
        self.factory.enableDefaultStackingForProduct(branch.product, branch)
        deferred = self.server.translateVirtualPath(
            '~%s/%s/.bzr/control.conf'
            % (branch.owner.name, branch.product.name))
        def check_control_file((transport, path)):
            self.assertEqual(
                'default_stack_on = /%s\n' % branch.unique_name,
                transport.get_bytes(path))
        return deferred.addCallback(check_control_file)

    def test_translate_branch_path_hosted(self):
        # translateVirtualPath returns a writable transport like that returned
        # by TransportDispatch.makeTransport for branches we can write to.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
        dispatch = self.server._transport_dispatch.makeTransport((
            BRANCH_TRANSPORT, {'id': branch.id, 'writable': True},
            '.bzr/README'))
        expected_transport, expected_path = dispatch

        deferred = self.server.translateVirtualPath(
            '%s/.bzr/README' % (branch.unique_name,))
        def check_branch_transport((transport, path)):
            self.assertEqual(expected_path, path)
            # Can't test for equality of transports, since URLs and object
            # identity differ.
            file_data = self.factory.getUniqueString()
            transport.mkdir(os.path.dirname(path))
            transport.put_bytes(path, file_data)
            self.assertEqual(file_data, expected_transport.get_bytes(path))
        return deferred.addCallback(check_branch_transport)

    def test_translate_branch_path_mirrored(self):
        # translateVirtualPath returns a read-only transport for branches we
        # can't write to.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        deferred = self.server.translateVirtualPath(
            '%s/.bzr/README' % (branch.unique_name,))
        def check_branch_transport((transport, path)):
            self.assertEqual('.bzr/README', path)
            self.assertEqual(True, transport.is_readonly())
        return deferred.addCallback(check_branch_transport)

    def test_createBranch_error_translation(self):
        # createBranch raises PermissionDenied if we try to create a branch
        # for, say, a product that doesn't exist.
        branch_url = '/~%s/no-such-product/new-branch' % (self.requester.name)
        deferred = self.server.createBranch(branch_url)
        deferred = self.assertFailure(deferred, errors.PermissionDenied)
        def check_exception(exception):
            self.assertEqual(branch_url, exception.path)
            self.assertEqual(
                ": Project 'no-such-product' does not exist.",
                exception.extra)
        return deferred.addCallback(check_exception)

    def test_get_url(self):
        # The URL of the server is 'lp-<number>:///', where <number> is the
        # id() of the server object. Including the id allows for multiple
        # Launchpad servers to be running within a single process.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())


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

    def test_translate_branch_path(self):
        branch = self.factory.makeAnyBranch()
        dispatch = self.server._transport_dispatch.makeTransport((
            BRANCH_TRANSPORT, {'id': branch.id, 'writable': True},
            '.bzr/README'))
        expected_transport, expected_path = dispatch

        deferred = self.server.translateVirtualPath(
            '%s/.bzr/README' % (branch.unique_name,))
        def check_branch_transport((transport, path)):
            self.assertEqual(expected_path, path)
            # Can't test for equality of transports, since URLs and object
            # identity differ.
            file_data = self.factory.getUniqueString()
            transport.mkdir(os.path.dirname(path))
            transport.put_bytes(path, file_data)
            self.assertEqual(file_data, expected_transport.get_bytes(path))
        return deferred.addCallback(check_branch_transport)

    def test_translate_control_dir_path(self):
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        branch = self.factory.makeProductBranch()
        branch.product.development_focus.branch = branch
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile, transport.list_dir, "~%s/%s/.bzr/"
            % (branch.owner.name, branch.product.name))

    def test_open_containing_raises_branch_not_found(self):
        # open_containing_from_transport raises NotBranchError if there's no
        # branch at that URL.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        branch = self.factory.makeAnyBranch(owner=self.requester)
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
        branch = self.factory.makeProductBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
        self.factory.enableDefaultStackingForProduct(branch.product, branch)
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
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        deferred = self._ensureDeferred(
            transport.get_bytes, '%s/.bzr/hello.txt' % branch.unique_name)
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_get_mapped_file_escaped_url(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport, even when the URL is escaped.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
        backing_transport = self._makeOnBackingTransport(branch)
        backing_transport.put_bytes('hello.txt', 'Hello World!')
        url = escape('%s/.bzr/hello.txt' % branch.unique_name)
        transport = self.getTransport()
        deferred = self._ensureDeferred(transport.get_bytes, url)
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_readv_mapped_file(self):
        # Using readv on a public branch URL gets chunks of the file as stored
        # on the base transport.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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
        # When createBranch raises faults.NotFound the transport should
        # translate this to a PermissionDenied exception (see the comment in
        # transport.py for why we translate to TransportNotPossible and not
        # NoSuchFile).
        transport = self.getTransport()
        return self.assertFiresFailureWithSubstring(
            errors.PermissionDenied, "does not exist", transport.mkdir,
            '~%s/no-such-product/some-name' % self.requester.name)

    def test_createBranch_permission_denied_error(self):
        # When createBranch raises faults.PermissionDenied, the transport
        # should translate this to a PermissionDenied exception.
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
                XMLRPCWrapper(self.authserver), self.requester.id,
                self.backing_transport, self.mirror_transport)
            self._server.setUp()
            self.addCleanup(self._server.tearDown)
        return self._server

    def test_no_mirrors_requested_if_no_branches_changed(self):
        self.assertEqual([], self._request_mirror_log)

    def test_creating_branch_requests_mirror(self):
        # Creating a branch requests a mirror.
        db_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
        branch = self.make_branch(db_branch.unique_name)
        self.assertEqual(
            [(self.requester.id, db_branch.id)], self._request_mirror_log)

    def test_branch_unlock_requests_mirror(self):
        # Unlocking a branch requests a mirror.
        db_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester)
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

        self.writable_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=self.requester).unique_name
        self.writable_file = '/%s/.bzr/hello.txt' % self.writable_branch
        self.read_only_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED).unique_name

        self.lp_server = self._setUpLaunchpadServer(
            self.requester.id, authserver, backing_transport,
            mirror_transport)
        self.lp_transport = get_transport(self.lp_server.get_url())
        self.lp_transport.mkdir(os.path.dirname(self.writable_file))
        self.lp_transport.put_bytes(self.writable_file, 'Hello World!')

    def _setUpMemoryServer(self):
        memory_server = MemoryServer()
        memory_server.setUp()
        self.addCleanup(memory_server.tearDown)
        return memory_server

    def _setUpLaunchpadServer(self, user_id, authserver, backing_transport,
                              mirror_transport):
        server = LaunchpadServer(
            XMLRPCWrapper(authserver), user_id, backing_transport,
            mirror_transport)
        server.setUp()
        self.addCleanup(server.tearDown)
        return server

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

