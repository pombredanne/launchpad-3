# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common helpers for codehosting tests."""

__metaclass__ = type
__all__ = ['AvatarTestCase', 'TwistedBzrlibLayer']

import os
import shutil
import threading

from canonical.testing import TwistedLayer, BzrlibLayer
from canonical.tests.test_twisted import TwistedTestCase

from twisted.internet import defer, threads


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


class TwistedBzrlibLayer(TwistedLayer, BzrlibLayer):
    """Use the Twisted reactor and Bazaar's temporary directory logic."""


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
    return decorated
