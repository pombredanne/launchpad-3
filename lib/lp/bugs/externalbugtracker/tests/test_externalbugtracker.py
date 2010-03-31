# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.interface import implements

from lp.bugs.externalbugtracker.base import ExternalBugTracker
from lp.bugs.externalbugtracker.debbugs import DebBugs

from lp.bugs.interfaces.externalbugtracker import (
    ISupportsBackLinking, ISupportsCommentImport, ISupportsCommentPushing)

from lp.testing import TestCase


class TestExternalBugTracker(TestCase):

    def test_sync_comments(self):
        # An ExternalBugTracker has a sync_comments attribute which is
        # represents when comment syncing is enabled.
        self.pushConfig('checkwatches', sync_comments=True)
        base_url = "http://www.example.com/"
        # A plain tracker will never support syncing comments.
        tracker = ExternalBugTracker(base_url)
        self.assertFalse(tracker.sync_comments)
        # Trackers that support comment pushing, comment pulling or
        # back-linking will have sync_comments set to True.
        class BackLinkingExternalBugTracker(ExternalBugTracker):
            implements(ISupportsBackLinking)
        tracker = BackLinkingExternalBugTracker(base_url)
        self.assertTrue(tracker.sync_comments)
        class CommentImportingExternalBugTracker(ExternalBugTracker):
            implements(ISupportsCommentImport)
        tracker = CommentImportingExternalBugTracker(base_url)
        self.assertTrue(tracker.sync_comments)
        class CommentPushingExternalBugTracker(ExternalBugTracker):
            implements(ISupportsCommentPushing)
        tracker = CommentPushingExternalBugTracker(base_url)
        self.assertTrue(tracker.sync_comments)
        # If syncing comments is globally disabled, sync_comments will
        # always be False.
        self.pushConfig('checkwatches', sync_comments=False)
        tracker = ExternalBugTracker(base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = BackLinkingExternalBugTracker(base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentImportingExternalBugTracker(base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentPushingExternalBugTracker(base_url)
        self.assertFalse(tracker.sync_comments)

    def test_sync_comments_for_debbugs(self):
        # Debian Bugs syncing can also be switched on and off using a
        # separate config variable, sync_debbugs_comments. DebBugs
        # supports comment pushing, comment import and back-linking.
        self.pushConfig(
            'checkwatches', sync_comments=True, sync_debbugs_comments=True)
        tracker = DebBugs("http://www.example.com/")
        self.assertTrue(tracker.sync_comments)
        # When it's disabled, syncing will always be disabled even
        # when sync_comments is set.
        self.pushConfig('checkwatches', sync_debbugs_comments=False)
        tracker = DebBugs("http://www.example.com/")
        self.assertFalse(tracker.sync_comments)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
