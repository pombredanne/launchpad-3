# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Laucnhpad code hosting Bazaar transport."""

__metaclass__ = type

import unittest

from bzrlib.transport import get_transport, _get_protocol_handlers
from bzrlib.transport.memory import MemoryTransport
from bzrlib.tests import TestCaseInTempDir, TestCaseWithMemoryTransport

from canonical.config import config
from canonical.codehosting import transport
from canonical.testing import reset_logging


def branch_id_to_path(branch_id):
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])


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
                (2, '+junk', [])]


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
        self.assertEqual(
            '00/00/00/01/',
            self.server.translate_virtual_path('/~foo/bar/baz'))
        self.assertEqual(
            '00/00/00/02/',
            self.server.translate_virtual_path('/~team1/bar/qux'))

    def test_extend_path_translation(self):
        self.assertEqual(
            '00/00/00/01/.bzr',
            self.server.translate_virtual_path('/~foo/bar/baz/.bzr'))

    def test_setUp(self):
        self.server.setUp()
        self.assertTrue(self.server.scheme in _get_protocol_handlers().keys())

    def test_tearDown(self):
        self.server.setUp()
        self.server.tearDown()
        self.assertFalse(self.server.scheme in _get_protocol_handlers().keys())

    def test_get_url(self):
        self.server.setUp()
        self.addCleanup(self.server.tearDown)
        self.assertEqual('lp-%d:///' % id(self.server), self.server.get_url())


class TestLaunchpadTransport(TestCaseWithMemoryTransport):

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.backing_transport = MemoryTransport()
        self.server = transport.LaunchpadServer(
            self.authserver, self.user_id, self.backing_transport)
        self.server.setUp()
        self.addCleanup(self.server.tearDown)

    def test_get_transport(self):
        transport = get_transport(self.server.get_url())
        self.assertEqual(self.server.get_url(), transport.base)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
