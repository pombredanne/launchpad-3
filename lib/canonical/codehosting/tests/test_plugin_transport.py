# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Launchpad code hosting Bazaar transport."""

__metaclass__ = type

import os
import unittest

from bzrlib import errors
from bzrlib.branch import Branch
from bzrlib.transport import get_transport, _get_protocol_handlers
from bzrlib.transport.memory import MemoryServer, MemoryTransport
from bzrlib.tests import TestCase

from canonical.authserver.interfaces import READ_ONLY, WRITABLE
from canonical.codehosting.tests.helpers import FakeLaunchpad
from canonical.codehosting.transport import LaunchpadServer, makedirs

from canonical.testing import BaseLayer


class TestLaunchpadServer(TestCase):

    # bzrlib manipulates 'logging'. The test runner will generate spurious
    # warnings if these manipulations are not cleaned up. BaseLayer does the
    # cleanup we need.
    layer = BaseLayer

    def setUp(self):
        TestCase.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.mirror_transport = MemoryTransport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport,
            self.mirror_transport)

    def test_construct(self):
        self.assertEqual(self.backing_transport, self.server.backing_transport)
        self.assertEqual(self.user_id, self.server.user_id)
        self.assertEqual('testuser', self.server.user_name)
        self.assertEqual(self.authserver, self.server.authserver)

    def test_base_path_translation(self):
        # Branches are stored on the filesystem by branch ID. This allows users
        # to rename and re-assign branches without causing unnecessary disk
        # churn. The ID is converted to four-byte hexadecimal and split into
        # four path segments, to make sure that the directory tree doesn't get
        # too wide and cause ext3 to have conniptions.
        #
        # However, branches are _accessed_ using their
        # ~person/product/branch-name. The server knows how to map this unique
        # name to the branch's path on the filesystem.

        # We can map a branch owned by the user to its path.
        self.assertEqual(
            ('00/00/00/01/', WRITABLE),
            self.server.translate_virtual_path('/~testuser/firefox/baz'))

        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        self.assertEqual(
            ('00/00/00/03/', WRITABLE),
            self.server.translate_virtual_path('/~testuser/+junk/random'))

        # We can map a branch owned by a team that the user is in to its path.
        self.assertEqual(
            ('00/00/00/04/', WRITABLE),
            self.server.translate_virtual_path('/~testteam/firefox/qux'))

        # The '+junk' product doesn't actually exist. It is used for branches
        # which don't have a product assigned to them.
        self.assertEqual(
            ('00/00/00/05/', READ_ONLY),
            self.server.translate_virtual_path('/~name12/+junk/junk.dev'))

    def test_extend_path_translation(self):
        # More than just the branch name needs to be translated: transports
        # will ask for files beneath the branch. The server translates the
        # unique name of the branch (i.e. the ~user/product/branch-name part)
        # to the four-byte hexadecimal split ID described in
        # test_base_path_translation and appends the remainder of the path.
        self.assertEqual(
            ('00/00/00/01/.bzr', WRITABLE),
            self.server.translate_virtual_path('/~testuser/firefox/baz/.bzr'))
        self.assertEqual(
            ('00/00/00/05/.bzr', READ_ONLY),
            self.server.translate_virtual_path('/~name12/+junk/junk.dev/.bzr'))

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
        self.assertFalse(self.server.scheme in _get_protocol_handlers().keys())

    def test_get_url(self):
        # The URL of the server is 'lp-<number>:///', where <number> is the
        # id() of the server object. Including the id allows for multiple
        # Launchpad servers to be running within a single process.
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())

    def test_nothing_dirty_by_default(self):
        # If a server is set up then torn down without any operations, then no
        # branches should be marked as dirty.
        self.server.setUp()
        self.server.tearDown()
        self.assertEqual([], self.server.authserver._request_mirror_log)

    def test_mark_as_dirty(self):
        # If a given file is flagged as modified then the branch owning that
        # file should be flagged as dirty.
        self.server.setUp()
        self.server.dirty('/~testuser/firefox/baz/.bzr')
        self.server.tearDown()
        self.assertEqual([1], self.server.authserver._request_mirror_log)

    def test_tearDown_clears_dirty_flags(self):
        # A branch is marked as dirty only for as long as the server is set up.
        # Once tearDown requests mirrors for all the dirty branches, the
        # branches are considered clean again, and thus not mirrored.
        self.server.setUp()
        self.server.dirty('/~testuser/firefox/baz/.bzr')
        self.server.tearDown()
        self.server.setUp()
        self.server.tearDown()
        self.assertEqual([1], self.server.authserver._request_mirror_log)


class TestLaunchpadTransport(TestCase):

    # See comment on TestLaunchpadServer.
    layer = BaseLayer

    def setUp(self):
        TestCase.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.mirror_transport = MemoryTransport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport,
            self.mirror_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.backing_transport.mkdir_multi(
            ['00', '00/00', '00/00/00', '00/00/00/01', '00/00/00/01/.bzr',
             '00/00/00/01/.bzr/branch', '00/00/00/01/.bzr/branch/lock'])
        self.backing_transport.put_bytes(
            '00/00/00/01/.bzr/hello.txt', 'Hello World!')

    def test_get_transport(self):
        # When the server is set up, getting a transport for the server URL
        # returns a LaunchpadTransport pointing at that URL. That is, the
        # transport is registered once the server is set up.
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)

    def test_get_mapped_file(self):
        # Getting a file from a public branch URL gets the file as stored on
        # the base transport.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            'Hello World!',
            transport.get_bytes('~testuser/firefox/baz/.bzr/hello.txt'))

    def test_put_mapped_file(self):
        # Putting a file from a public branch URL stores the file in the mapped
        # URL on the base transport.
        transport = get_transport(self.server.get_url())
        transport.put_bytes(
            '~testuser/firefox/baz/.bzr/goodbye.txt', "Goodbye")
        self.assertEqual(
            "Goodbye",
            self.backing_transport.get_bytes('00/00/00/01/.bzr/goodbye.txt'))

    def test_cloning_updates_base(self):
        # A transport can be constructed using a path relative to another
        # transport by using 'clone'. When this happens, it's necessary for the
        # newly constructed transport to preserve the non-relative path
        # information from the transport being cloned. It's necessary because
        # the transport needs to have the '~user/product/branch-name' in order
        # to translate paths.
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)
        transport = transport.clone('~testuser')
        self.assertEqual(self.server.get_url() + '~testuser', transport.base)

    def test_abspath_without_schema(self):
        # _abspath returns the absolute path for a given relative path, but
        # without the schema part of the URL that is included by abspath.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            '/~testuser/firefox/baz',
            transport._abspath('~testuser/firefox/baz'))
        transport = transport.clone('~testuser')
        self.assertEqual(
            '/~testuser/firefox/baz', transport._abspath('firefox/baz'))

    def test_cloning_preserves_path_mapping(self):
        # The public branch URL -> filesystem mapping uses the base URL to do
        # its mapping, thus ensuring that clones map correctly.
        transport = get_transport(self.server.get_url())
        transport = transport.clone('~testuser')
        self.assertEqual(
            'Hello World!', transport.get_bytes('firefox/baz/.bzr/hello.txt'))

    def test_abspath(self):
        # abspath for a relative path is the same as the base URL for a clone
        # for that relative path.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            transport.clone('~testuser').base, transport.abspath('~testuser'))

    def test_incomplete_path_not_found(self):
        # For a branch URL to be complete, it needs to have a person, product
        # and branch. Trying to perform operations on an incomplete URL raises
        # an error. Which kind of error is not particularly important.
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile, transport.get, '~testuser')

    def test_complete_non_existent_path_not_found(self):
        # Bazaar looks for files inside a branch directory before it looks for
        # the branch itself. If the branch doesn't exist, any files it asks for
        # are not found. i.e. we raise NoSuchFile
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile,
            transport.get, '~testuser/firefox/new-branch/.bzr/branch-format')

    def test_rename(self):
        # We can use the transport to rename files where both the source and
        # target are virtual paths.
        transport = get_transport(self.server.get_url())
        dir_contents = set(transport.list_dir('~testuser/firefox/baz/.bzr'))
        transport.rename(
            '~testuser/firefox/baz/.bzr/hello.txt',
            '~testuser/firefox/baz/.bzr/goodbye.txt')
        dir_contents.remove('hello.txt')
        dir_contents.add('goodbye.txt')
        self.assertEqual(
            set(transport.list_dir('~testuser/firefox/baz/.bzr')),
            dir_contents)
        self.assertEqual(
            set(self.backing_transport.list_dir('00/00/00/01/.bzr')),
            dir_contents)

    def test_iter_files_recursive(self):
        # iter_files_recursive doesn't take a relative path but still needs to
        # do a path-based operation on the backing transport, so the
        # implementation can't just be a shim to the backing transport.
        transport = get_transport(self.server.get_url())
        files = list(
            transport.clone('~testuser/firefox/baz').iter_files_recursive())
        backing_transport = self.backing_transport.clone('00/00/00/01')
        self.assertEqual(list(backing_transport.iter_files_recursive()), files)

    def test_make_two_directories(self):
        # Bazaar doesn't have a makedirs() facility for transports, so we need
        # to make sure that we can make a directory on the backing transport if
        # its parents exist and if they don't exist.
        transport = get_transport(self.server.get_url())
        transport.mkdir('~testuser/thunderbird/banana')
        transport.mkdir('~testuser/thunderbird/orange')
        self.assertTrue(transport.has('~testuser/thunderbird/banana'))
        self.assertTrue(transport.has('~testuser/thunderbird/orange'))

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

    def test_lock_marks_as_dirty(self):
        # Locking a branch marks it as dirty.
        self.lockBranch('~testuser/firefox/baz')
        try:
            self.assertEqual(set([1]), self.server._dirty_branch_ids)
        finally:
            self.unlockBranch('~testuser/firefox/baz')

#     def test_unlock_requests_mirror(self):
#         # Unlocking a branch requests a mirror.
#         self.lockBranch('~testuser/firefox/baz')
#         self.unlockBranch('~testuser/firefox/baz')
#         self.assertEqual([1], self.server.authserver._request_mirror_log)


class TestLaunchpadTransportReadOnly(TestCase):
    """Tests for read-only operations on the LaunchpadTransport."""

    # See comment on TestLaunchpadServer.
    layer = BaseLayer

    def setUp(self):
        TestCase.setUp(self)
        _memory_server = MemoryServer()
        _memory_server.setUp()
        self.addCleanup(_memory_server.tearDown)
        mirror_transport = get_transport(_memory_server.get_url())

        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.server = LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport,
            mirror_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.transport = get_transport(self.server.get_url())
        path = self.server.translate_virtual_path(
            '/~testuser/firefox/baz/.bzr')[0]
        makedirs(self.backing_transport, path)
        self.backing_transport.put_bytes(
            os.path.join(path, 'hello.txt'), 'Hello World!')
        path = self.server.translate_virtual_path(
            '/~name12/+junk/junk.dev/.bzr')[0]
        makedirs(self.backing_transport, path)
        t = self.backing_transport.clone(path)
        t.put_bytes('README', 'Hello World!')
        makedirs(mirror_transport, path)
        mirror_transport.clone(path).put_bytes('README', 'Goodbye World!')

    def test_mkdir_readonly(self):
        # If we only have READ_ONLY access to a branch then we should not be
        # able to create directories within that branch.
        self.assertRaises(
            errors.TransportNotPossible,
            self.transport.mkdir, '~name12/+junk/junk.dev/.bzr')

    def test_rename_target_readonly(self):
        # Even if we can write to a file, we can't rename it to location which
        # is read-only to us.
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.TransportNotPossible,
            self.transport.rename, '/~testuser/firefox/baz/.bzr/hello.txt',
            '/~name12/+junk/junk.dev/.bzr/goodbye.txt')

    def test_readonly_refers_to_mirror(self):
        # Read-only operations should get their data from the mirror, not the
        # primary backing transport.
        # XXX: JonathanLange 2007-06-21, Explain more of this.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            'Goodbye World!',
            transport.get_bytes('/~name12/+junk/junk.dev/.bzr/README'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
