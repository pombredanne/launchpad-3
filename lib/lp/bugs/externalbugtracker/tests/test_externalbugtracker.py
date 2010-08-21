# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the externalbugtracker package."""

__metaclass__ = type

import unittest

from zope.interface import implements

from lp.bugs.externalbugtracker.base import ExternalBugTracker
from lp.bugs.externalbugtracker.debbugs import DebBugs
from lp.bugs.interfaces.externalbugtracker import (
    ISupportsBackLinking,
    ISupportsCommentImport,
    ISupportsCommentPushing,
    )
from lp.testing import TestCase


class BackLinkingExternalBugTracker(ExternalBugTracker):
    implements(ISupportsBackLinking)

class CommentImportingExternalBugTracker(ExternalBugTracker):
    implements(ISupportsCommentImport)

class CommentPushingExternalBugTracker(ExternalBugTracker):
    implements(ISupportsCommentPushing)


class TestCheckwatchesConfig(TestCase):

    base_url = "http://www.example.com/"

    def test_sync_comments_enabled(self):
        # If the global config checkwatches.sync_comments is True,
        # external bug trackers will set their sync_comments attribute
        # according to their support of comment syncing.
        self.pushConfig('checkwatches', sync_comments=True)
        # A plain tracker will never support syncing comments.
        tracker = ExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        # Trackers that support comment pushing, comment pulling or
        # back-linking will have sync_comments set to True.
        tracker = BackLinkingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)
        tracker = CommentImportingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)
        tracker = CommentPushingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)

    def test_sync_comments_disabled(self):
        # If the global config checkwatches.sync_comments is False,
        # external bug trackers will always set their sync_comments
        # attribute to False.
        self.pushConfig('checkwatches', sync_comments=False)
        tracker = ExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = BackLinkingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentImportingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentPushingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)

    def test_sync_debbugs_comments_enabled(self):
        # Debian Bugs syncing can also be switched on and off using a
        # separate config variable, sync_debbugs_comments. DebBugs
        # supports comment pushing and import.
        self.pushConfig(
            'checkwatches', sync_comments=True, sync_debbugs_comments=True)
        tracker = DebBugs(self.base_url)
        self.assertTrue(tracker.sync_comments)
        # When either sync_comments or sync_debbugs_comments is False
        # (or both), the Debian Bugs external bug tracker will claim
        # to not support any form of comment syncing.
        self.pushConfig(
            'checkwatches', sync_comments=True, sync_debbugs_comments=False)
        tracker = DebBugs(self.base_url)
        self.assertFalse(tracker.sync_comments)
        self.pushConfig(
            'checkwatches', sync_comments=False, sync_debbugs_comments=True)
        tracker = DebBugs(self.base_url)
        self.assertFalse(tracker.sync_comments)
        self.pushConfig(
            'checkwatches', sync_comments=False, sync_debbugs_comments=False)
        tracker = DebBugs(self.base_url)
        self.assertFalse(tracker.sync_comments)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
