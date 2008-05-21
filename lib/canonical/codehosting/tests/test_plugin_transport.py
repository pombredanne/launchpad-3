# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Launchpad code hosting Bazaar transport."""

__metaclass__ = type

import codecs
import logging
import os
from StringIO import StringIO
import shutil
import sys
import tempfile
import unittest

from bzrlib import errors
from bzrlib.transport import (
    get_transport, _get_protocol_handlers, register_transport, Server,
    unregister_transport)
from bzrlib.transport.memory import MemoryServer, MemoryTransport
from bzrlib.tests import TestCase as BzrTestCase, TestCaseInTempDir
from bzrlib.urlutils import local_path_to_url

from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.authserver.interfaces import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE)
from canonical.codehosting import branch_id_to_path
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.sftp import FatLocalTransport
from canonical.codehosting.tests.helpers import FakeLaunchpad
from canonical.codehosting.transport import (
    AsyncLaunchpadTransport, BlockingProxy, InvalidControlDirectory,
    LaunchpadServer, set_up_logging, VirtualTransport)
from canonical.config import config
from canonical.testing import BaseLayer, reset_logging


class TestLaunchpadServer(TrialTestCase, BzrTestCase):

    # bzrlib manipulates 'logging'. The test runner will generate spurious
    # warnings if these manipulations are not cleaned up. BaseLayer does the
    # cleanup we need.
    layer = BaseLayer

    def setUp(self):
        BzrTestCase.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.mirror_transport = MemoryTransport()
        self.server = LaunchpadServer(
            BlockingProxy(self.authserver), self.user_id,
            self.backing_transport, self.mirror_transport)

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
        deferred = self.server.translateVirtualPath('/~testuser/firefox/baz')
        deferred.addCallback(
            self.assertEqual,
            (self.server._backing_transport, '00/00/00/01/'))
        return deferred

    def test_base_path_translation_junk_branch(self):
        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        deferred = self.server.translateVirtualPath('/~testuser/+junk/random')
        deferred.addCallback(
            self.assertEqual,
            (self.server._backing_transport, '00/00/00/03/'))
        return deferred

    def test_base_path_translation_team_branch(self):
        # We can map a branch owned by a team that the user is in to its path.
        deferred = self.server.translateVirtualPath('/~testteam/firefox/qux')
        deferred.addCallback(
            self.assertEqual,
            (self.server._backing_transport, '00/00/00/04/'))
        return deferred

    def test_base_path_translation_team_junk_branch(self):
        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        deferred = self.server.translateVirtualPath('/~name12/+junk/junk.dev')
        deferred.addCallback(
            self.assertEqual,
            (self.server._mirror_transport, '00/00/00/05/'))
        return deferred

    def test_extend_path_translation_on_backing(self):
        # More than just the branch name needs to be translated: transports
        # will ask for files beneath the branch. The server translates the
        # unique name of the branch (i.e. the ~user/product/branch-name part)
        # to the four-byte hexadecimal split ID described in
        # test_base_path_translation and appends the remainder of the path.
        deferred = self.server.translateVirtualPath(
            '/~testuser/firefox/baz/.bzr')
        deferred.addCallback(
            self.assertEqual,
            (self.server._backing_transport, '00/00/00/01/.bzr'))
        return deferred

    def test_extend_path_translation_on_mirror(self):
        deferred = self.server.translateVirtualPath(
            '/~name12/+junk/junk.dev/.bzr')
        deferred.addCallback(
            self.assertEqual,
            (self.server._mirror_transport, '00/00/00/05/.bzr'))
        return deferred

    def test_setUp(self):
        # Setting up the server registers its schema with the protocol
        # handlers.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertTrue(self.server.scheme in _get_protocol_handlers().keys())

    def test_tearDown(self):
        # Setting up then tearing down the server removes its schema from the
        # protocol handlers.
        self.server.setUp()
        self.server.tearDown()
        self.assertFalse(
            self.server.scheme in _get_protocol_handlers().keys())

    def test_noMirrorsRequestedIfNoBranchesChanged(self):
        # Starting up and shutting down the server will send no mirror
        # requests.
        self.server.setUp()
        self.server.tearDown()
        self.assertEqual([], self.authserver._request_mirror_log)

    def test_get_url(self):
        # The URL of the server is 'lp-<number>:///', where <number> is the
        # id() of the server object. Including the id allows for multiple
        # Launchpad servers to be running within a single process.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())

    def test_translationIsCached(self):
        # We don't go to the authserver for every path translation.
        #
        # To test this, we translate a branch and then delete that branch on
        # the authserver. If the cache is operating, the next attempt to
        # translate that branch should succeed with the same value as the
        # first attempt.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

        # ~testuser/firefox/baz is branch 1.
        deferred = self.server.translateVirtualPath(
            '~testuser/firefox/baz/.bzr')

        def assert_path_starts_with(branch_info, expected_path):
            transport, path = branch_info
            self.assertStartsWith(path, expected_path)

        def futz_with_authserver(ignored):
            # Delete the branch on the authserver.
            del self.authserver._branch_set[1]
            branch_info = self.authserver.getBranchInformation(
                1, 'testuser', 'firefox', 'baz')
            # The authserver says there is no ~testuser/firefox/baz branch.
            self.assertEqual(('', ''), branch_info)

        deferred.addCallback(assert_path_starts_with, branch_id_to_path(1))
        deferred.addCallback(futz_with_authserver)
        deferred.addCallback(
            lambda ignored: self.server.translateVirtualPath(
                    '~testuser/firefox/baz/.bzr'))
        deferred.addCallback(assert_path_starts_with, branch_id_to_path(1))
        return deferred

    def test_translateControlPath(self):
        deferred = self.server.translateVirtualPath(
            '~testuser/evolution/.bzr/control.conf')
        def check_control_file((transport, path)):
            self.assertEqual(
                'default_stack_on=%s~vcs-imports/evolution/main\n'
                % config.codehosting.supermirror_root,
                transport.get_bytes(path))
        return deferred.addCallback(check_control_file)

    def test_buildControlDirectory(self):
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

        branch = '~user/product/branch'
        transport = self.server._buildControlDirectory(branch)
        self.assertEqual(
            'default_stack_on=%s%s\n' % (
                config.codehosting.supermirror_root, branch),
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


class TestVirtualTransport(TestCaseInTempDir):

    class VirtualServer(Server):
        """Very simple server that provides a VirtualTransport."""

        def __init__(self, backing_transport):
            self._backing_transport = backing_transport

        def _factory(self, url):
            return VirtualTransport(self, url)

        def get_url(self):
            return self.scheme

        def setUp(self):
            self.scheme = 'virtual:///'
            register_transport(self.scheme, self._factory)

        def tearDown(self):
            unregister_transport(self.scheme, self._factory)

        def translateVirtualPath(self, virtual_path):
            return defer.succeed(
                (self._backing_transport,
                 'prefix_' + virtual_path.lstrip('/')))

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.server = self.VirtualServer(
            FatLocalTransport(local_path_to_url('.')))
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.transport = get_transport(self.server.get_url())

    def test_writeChunk(self):
        self.transport.writeChunk('foo', 0, 'content')
        self.assertEqual('content', open('prefix_foo').read())

    def test_realPath(self):
        # local_realPath returns the real, absolute path to a file, resolving
        # any symlinks.
        self.transport.mkdir('baz')
        os.symlink('prefix_foo', 'prefix_baz/bar')
        t = self.transport.clone('baz')
        self.assertEqual('/baz/bar', t.local_realPath('bar'))


class LaunchpadTransportTests:
    """Tests for a Launchpad transport.

    These tests are expected to run against two kinds of transport.
      1. An asynchronous one that returns Deferreds.
      2. A synchronous one that returns actual values.

    To support that, subclasses must implement `getTransport` and
    `_ensureDeferred`. See these methods for more information.
    """

    # See comment on TestLaunchpadServer.
    layer = BaseLayer

    def setUp(self):
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.mirror_transport = MemoryTransport()
        self.server = self.getServer(
            self.authserver, self.user_id, self.backing_transport,
            self.mirror_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.backing_transport.mkdir_multi(
            ['00', '00/00', '00/00/00', '00/00/00/01', '00/00/00/01/.bzr',
             '00/00/00/01/.bzr/branch', '00/00/00/01/.bzr/branch/lock'])
        self.backing_transport.put_bytes(
            '00/00/00/01/.bzr/hello.txt', 'Hello World!')

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
            BlockingProxy(authserver), user_id, backing_transport,
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

    def test_get_mapped_file(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport.
        transport = self.getTransport()
        deferred = self._ensureDeferred(
            transport.get_bytes, '~testuser/firefox/baz/.bzr/hello.txt')
        return deferred.addCallback(self.assertEqual, 'Hello World!')

    def test_readv_mapped_file(self):
        # Using readv on a public branch URL gets chunks of the file as stored
        # on the base transport.
        transport = self.getTransport()
        deferred = self._ensureDeferred(
            transport.readv, '~testuser/firefox/baz/.bzr/hello.txt',
            [(3, 2)])
        def get_chunk(generator):
            return generator.next()[1]
        deferred.addCallback(get_chunk)
        return deferred.addCallback(self.assertEqual, 'lo')

    def test_put_mapped_file(self):
        # Putting a file from a public branch URL stores the file in the
        # mapped URL on the base transport.
        transport = self.getTransport()
        deferred = self._ensureDeferred(
            transport.put_bytes,
            '~testuser/firefox/baz/.bzr/goodbye.txt', "Goodbye")
        def check_bytes_written(ignored):
            self.assertEqual(
                "Goodbye",
                self.backing_transport.get_bytes(
                    '00/00/00/01/.bzr/goodbye.txt'))
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
        transport = transport.clone('~testuser')
        deferred = self._ensureDeferred(
            transport.get_bytes, 'firefox/baz/.bzr/hello.txt')
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
        transport = self.getTransport()
        deferred = self._ensureDeferred(
            transport.list_dir, '~testuser/firefox/baz/.bzr')
        deferred.addCallback(set)

        def rename_file(dir_contents):
            """Rename a file and return the original directory contents."""
            deferred = self._ensureDeferred(
                transport.rename,
                '~testuser/firefox/baz/.bzr/hello.txt',
                '~testuser/firefox/baz/.bzr/goodbye.txt')
            deferred.addCallback(lambda ignored: dir_contents)
            return deferred

        def check_file_was_renamed(dir_contents):
            """Check that the old name isn't there and the new name is."""
            # Replace the old name with the new name.
            dir_contents.remove('hello.txt')
            dir_contents.add('goodbye.txt')
            deferred = self._ensureDeferred(
                transport.list_dir, '~testuser/firefox/baz/.bzr')
            deferred.addCallback(set)
            # Check against the virtual transport.
            deferred.addCallback(self.assertEqual, dir_contents)
            # Check against the backing transport.
            deferred.addCallback(
                lambda ignored:
                self.assertEqual(
                    set(self.backing_transport.list_dir('00/00/00/01/.bzr')),
                    dir_contents))
            return deferred
        deferred.addCallback(rename_file)
        return deferred.addCallback(check_file_was_renamed)

    def test_iter_files_recursive(self):
        # iter_files_recursive doesn't take a relative path but still needs to
        # do a path-based operation on the backing transport, so the
        # implementation can't just be a shim to the backing transport.
        transport = self.getTransport().clone('~testuser/firefox/baz')
        backing_transport = self.backing_transport.clone('00/00/00/01')
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
        transport = self.getTransport()
        transport.mkdir('~testuser/thunderbird/banana')
        transport.mkdir('~testuser/thunderbird/orange')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))
        self.assertTrue(transport.has('~testuser/thunderbird/orange'))

    def setFailingBranchDetails(self, name, code, message):
        """Arrange that calling createBranch with a given branch name fails.

        After calling this, calling self.authserver.createBranch with a
        branch_name of 'name' with raise a fault with 'code' and 'message' as
        faultCode and faultString respectively.
        """
        self.authserver.failing_branch_name = name
        self.authserver.failing_branch_code = code
        self.authserver.failing_branch_string = message

    def test_createBranch_not_found_error(self):
        # When createBranch raises an exception with faultCode
        # NOT_FOUND_FAULT_CODE, the transport should translate this to
        # a TransportNotPossible exception (see the comment in
        # transport.py for why we translate to TransportNotPossible
        # and not NoSuchFile).
        transport = self.getTransport()
        message = "Branch exploding, as requested."
        self.setFailingBranchDetails(
            'explode!', NOT_FOUND_FAULT_CODE, message)
        return self.assertFiresFailureWithSubstring(
            errors.PermissionDenied, message,
            transport.mkdir, '~testuser/thunderbird/explode!')

    def test_createBranch_permission_denied_error(self):
        # When createBranch raises an exception with faultCode
        # PERMISSION_DENIED_FAULT_CODE, the transport should translate
        # this to a PermissionDenied exception.
        transport = self.getTransport()
        message = "Branch exploding, as requested."
        self.setFailingBranchDetails(
            'explode!', PERMISSION_DENIED_FAULT_CODE, message)
        return self.assertFiresFailureWithSubstring(
            errors.PermissionDenied, message,
            transport.mkdir, '~testuser/thunderbird/explode!')

    def lockBranch(self, unique_name):
        """Simulate locking a branch."""
        transport = get_transport(self.server.get_url() + unique_name)
        transport = transport.clone('.bzr/branch/lock')
        transport.mkdir('temporary')
        # It's this line that actually locks the branch.
        transport.rename('temporary', 'held')

    def unlockBranch(self, unique_name):
        """Simulate unlocking a branch."""
        transport = get_transport(self.server.get_url() + unique_name)
        transport = transport.clone('.bzr/branch/lock')
        # Actually unlock the branch.
        transport.rename('held', 'temporary')
        transport.rmdir('temporary')

    def test_unlock_requests_mirror(self):
        # Unlocking a branch requests a mirror.
        self.lockBranch('~testuser/firefox/baz')
        self.unlockBranch('~testuser/firefox/baz')
        self.assertEqual(
            [(self.user_id, 1)], self.authserver._request_mirror_log)

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


class TestLaunchpadTransportReadOnly(TrialTestCase, BzrTestCase):
    """Tests for read-only operations on the LaunchpadTransport."""

    # See comment on TestLaunchpadServer.
    layer = BaseLayer

    def setUp(self):
        BzrTestCase.setUp(self)

        memory_server = self._setUpMemoryServer()
        memory_transport = get_transport(memory_server.get_url())
        backing_transport = memory_transport.clone('backing')
        mirror_transport = memory_transport.clone('mirror')

        self.lp_server = self._setUpLaunchpadServer(
            backing_transport, mirror_transport)
        self.lp_transport = get_transport(self.lp_server.get_url())

        self.writable_file = '/~testuser/firefox/baz/.bzr/hello.txt'
        self.file_on_both_transports = '/~name12/+junk/junk.dev/.bzr/README'
        self.file_on_mirror_only = '/~name12/+junk/junk.dev/.bzr/MIRROR-ONLY'

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

    def _setUpLaunchpadServer(self, backing_transport, mirror_transport):
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        server = LaunchpadServer(
            BlockingProxy(self.authserver), self.user_id, backing_transport,
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
            self.lp_transport.mkdir, '~name12/+junk/junk.dev/.bzr')

    def test_rename_target_readonly(self):
        # Even if we can write to a file, we can't rename it to location which
        # is read-only to us.
        self.assertRaises(
            errors.TransportNotPossible,
            self.lp_transport.rename, self.writable_file,
            '/~name12/+junk/junk.dev/.bzr/goodbye.txt')

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
        read_only_branch_name = '/~name12/+junk/junk.dev/'
        transport = self.lp_transport.clone(read_only_branch_name)
        files = list(transport.iter_files_recursive())

        mirror_only = self.file_on_mirror_only[len(read_only_branch_name):]
        self.assertTrue(
            mirror_only in files, '%r not in %r' % (mirror_only, files))

    def test_listable_refers_to_mirror(self):
        # listable() refers to the mirror transport for read-only branches.
        read_only_branch_name = '/~name12/+junk/junk.dev/'
        transport = self.lp_transport.clone(read_only_branch_name)

        # listable() returns the same value for both transports. To
        # distinguish them, we'll monkey patch the mirror and backing
        # transports.
        self.lp_server._mirror_transport.listable = lambda: 'mirror'
        self.lp_server._backing_transport.listable = lambda: 'backing'

        self.assertEqual('mirror', transport.listable())


class TestLoggingSetup(BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Configure the debug logfile
        self._real_debug_logfile = config.codehosting.debug_logfile
        file_handle, filename = tempfile.mkstemp()
        config.codehosting.debug_logfile = filename

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

        # We want to use Bazaar's default logging -- not its test logging --
        # so here we disable the testing logging system (which restores
        # default logging).
        self._finishLogFile()

    def tearDown(self):
        sys.stderr = self._real_stderr
        config.codehosting.debug_logfile = self._real_debug_logfile
        BzrTestCase.tearDown(self)
        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        reset_logging()

    def test_loggingSetUpAssertionFailsIfParentDirectoryIsNotADirectory(self):
        # set_up_logging fails with an AssertionError if it cannot create the
        # directory that the log file will go in.
        file_handle, filename = tempfile.mkstemp()
        def remove_file():
            os.unlink(filename)
        self.addCleanup(remove_file)

        config.codehosting.debug_logfile = os.path.join(filename, 'debug.log')
        self.assertRaises(AssertionError, set_up_logging)

    def test_makesLogDirectory(self):
        # If the specified logfile is in a directory that doesn't exist, then
        # set_up_logging makes that directory.
        directory = tempfile.mkdtemp()
        def remove_directory():
            shutil.rmtree(directory)
        self.addCleanup(remove_directory)

        config.codehosting.debug_logfile = os.path.join(
            directory, 'subdir', 'debug.log')
        set_up_logging()
        self.failUnless(os.path.isdir(os.path.join(directory, 'subdir')))

    def test_returnsCodehostingLogger(self):
        # set_up_logging returns the 'codehosting' logger.
        self.assertIs(set_up_logging(), logging.getLogger('codehosting'))

    def test_codehostingLogGoesToDebugLogfile(self):
        # Once set_up_logging is called, messages logged to the codehosting
        # logger are stored in config.codehosting.debug_logfile.

        set_up_logging()

        # Make sure that a logged message goes to the debug logfile
        logging.getLogger('codehosting').debug('Hello hello')
        self.failUnless(
            open(config.codehosting.debug_logfile).read().endswith(
                'Hello hello\n'))

    def test_codehostingLogDoesntGoToStderr(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.

        set_up_logging()

        # Make sure that a logged message does not go to stderr.
        logging.getLogger('codehosting').info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')

    def test_codehostingLogDoesntGoToStderrEvenWhenNoLogfile(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr, even if there's
        # no debug_logfile set.

        config.codehosting.debug_logfile = None
        set_up_logging()

        # Make sure that a logged message does not go to stderr.
        logging.getLogger('codehosting').info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')

    def test_leavesBzrHandlersUnchanged(self):
        # Bazaar's log handling is untouched by set_up_logging.
        root_handlers = logging.getLogger('').handlers
        bzr_handlers = logging.getLogger('bzr').handlers

        set_up_logging()

        self.assertEqual(root_handlers, logging.getLogger('').handlers)
        self.assertEqual(bzr_handlers, logging.getLogger('bzr').handlers)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
