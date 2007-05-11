# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for supermirrorsftp tests."""

__metaclass__ = type
__all__ = ['AvatarTestCase']

import os
import shutil

from canonical.tests.test_twisted import TwistedTestCase


class AvatarTestCase(TwistedTestCase):
    """Base class for tests that need an SFTPOnlyAvatar with some basic sample
    data."""
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
