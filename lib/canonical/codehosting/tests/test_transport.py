# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Laucnhpad code hosting Bazaar transport."""

__metaclass__ = type

import unittest

from bzrlib.transport import get_transport
from bzrlib.tests import TestCase

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
        return [(1, 'bar', [(1, 'baz'), (2, 'qux')])]


class TestLaunchpadTransport(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.authserver = FakeLaunchpad()
        self.user_id = 1
        self.server = transport.LaunchpadServer(
            self.authserver, self.user_id)

    def test_base_path_translation(self):
        self.assertEqual('00/00/00/01/',
                         self.server.translate_relpath('~foo/bar/baz'))
        self.assertEqual('00/00/00/02/',
                         self.server.translate_relpath('~team1/bar/qux'))

    def test_extend_path_translation(self):
        self.assertEqual('00/00/00/01/.bzr',
                         self.server.translate_relpath('~foo/bar/baz/.bzr'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
