# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Laucnhpad code hosting Bazaar transport."""

__metaclass__ = type

import unittest

from bzrlib import errors
from bzrlib.transport import get_transport, _get_protocol_handlers
from bzrlib.transport.memory import MemoryTransport
from bzrlib.tests import TestCaseInTempDir, TestCaseWithMemoryTransport

from canonical.codehosting import transport


class FakeLaunchpad:

    def getUser(self, loginID):
        assert loginID == 1, \
               "The Launchpad transport will always know the user id."
        return {'id': loginID, 'displayname': 'Test User',
                'emailaddresses': ['test@test.com'],
                'wikiname': 'TestUser',
                'teams': [{'id': 2, 'name': 'foo', 'displayname': 'Test User'},
                          {'id': 3, 'name': 'team1', 'displayname': 'Test Team'}]}

    def getBranchesForUser(self, personID):
        return [(1, 'bar', [(1, 'baz'), (2, 'qux')]),
                (2, '', [(3, 'random')])]


class TestLaunchpadServer(TestCaseInTempDir):

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.server = transport.LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)

    def test_construct(self):
        self.assertEqual(self.backing_transport, self.server.backing_transport)
        self.assertEqual(self.user_id, self.server.user_id)
        self.assertEqual(self.authserver, self.server.authserver)

    def test_base_path_translation(self):
        # ~person/product/branch maps to the branch ID converted to a four byte
        # hexadecimal number and then split into four path segments.
        self.assertEqual(
            '00/00/00/01/',
            self.server.translate_virtual_path('/~foo/bar/baz'))
        self.assertEqual(
            '00/00/00/02/',
            self.server.translate_virtual_path('/~team1/bar/qux'))
        self.assertEqual(
            '00/00/00/03/',
            self.server.translate_virtual_path('/~foo/+junk/random'))

    def test_extend_path_translation(self):
        # Trailing path segments are preserved.
        self.assertEqual(
            '00/00/00/01/.bzr',
            self.server.translate_virtual_path('/~foo/bar/baz/.bzr'))

    def test_setUp(self):
        # Setting up the server registers its schema with the protocol
        # handlers.
        self.server.setUp()
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


class TestLaunchpadTransport(TestCaseWithMemoryTransport):

    def setUp(self):
        TestCaseWithMemoryTransport.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = self.get_transport()
        self.server = transport.LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.backing_transport.mkdir_multi(
            ['00', '00/00', '00/00/00', '00/00/00/01'])
        self.backing_transport.put_bytes(
            '00/00/00/01/hello.txt', 'Hello World!')

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
            'Hello World!', transport.get_bytes('~foo/bar/baz/hello.txt'))

    def test_put_mapped_file(self):
        # Putting a file from a public branch URL stores the file in the mapped
        # URL on the base transport.
        transport = get_transport(self.server.get_url())
        transport.put_bytes('~foo/bar/baz/goodbye.txt', "Goodbye")
        self.assertEqual(
            "Goodbye",
            self.backing_transport.get_bytes('00/00/00/01/goodbye.txt'))

    def test_cloning_updates_base(self):
        # Cloning a LaunchpadTransport returns a new transport with the base
        # URL equal to the base URL of the original with the relative path
        # appended.
        # XXX - That's bad prose - Jonathan Lange, 2007-05-25
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)
        transport = transport.clone('~foo')
        self.assertEqual(self.server.get_url() + '~foo', transport.base)

    def test_abspath_without_schema(self):
        # _abspath returns the absolute path for a given relative path, but
        # without the schema part of the URL that is included by abspath.
        transport = get_transport(self.server.get_url())
        self.assertEqual('/~foo/bar/baz', transport._abspath('~foo/bar/baz'))
        transport = transport.clone('~foo')
        self.assertEqual('/~foo/bar/baz', transport._abspath('bar/baz'))

    def test_cloning_preserves_path_mapping(self):
        # The public branch URL -> filesystem mapping uses the base URL to do
        # its mapping, thus ensuring that clones map correctly.
        transport = get_transport(self.server.get_url())
        transport = transport.clone('~foo')
        self.assertEqual(
            'Hello World!', transport.get_bytes('bar/baz/hello.txt'))

    def test_abspath(self):
        # abspath for a relative path is the same as the base URL for a clone
        # for that relative path.
        transport = get_transport(self.server.get_url())
        self.assertEqual(
            transport.clone('~foo').base, transport.abspath('~foo'))

    def test_incomplete_path_not_found(self):
        # For a branch URL to be complete, it needs to have a person, product
        # and branch. Trying to perform operations on an incomplete URL raises
        # NoSuchFile errors.
        transport = get_transport(self.server.get_url())
        self.assertRaises(
            errors.NoSuchFile, transport.get, '~foo')

    def test_rename(self):
        # rename needs to translate the target path as well as the source path,
        # so we need a separate test for it.
        transport = get_transport(self.server.get_url())
        transport.rename('~foo/bar/baz/hello.txt', '~foo/bar/baz/goodbye.txt')
        self.assertEqual(['goodbye.txt'], transport.list_dir('~foo/bar/baz'))
        self.assertEqual(['goodbye.txt'],
                         self.backing_transport.list_dir('00/00/00/01'))

    def test_iter_files_recursive(self):
        # iter_files_recursive doesn't take a relative path but still needs to
        # do a path-based operation on the backing transport. Thus, we need a
        # separate test for it.
        transport = get_transport(self.server.get_url())
        files = list(transport.clone('~foo/bar/baz').iter_files_recursive())
        backing_transport = self.backing_transport.clone('00/00/00/01')
        self.assertEqual(list(backing_transport.iter_files_recursive()), files)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
