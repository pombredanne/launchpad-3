# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Checkwatches unit tests."""

__metaclass__ = type

import unittest
import transaction

from zope.component import getUtility

from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.testing import LaunchpadZopelessLayer

from lp.bugs.externalbugtracker.bugzilla import BugzillaAPI
from lp.bugs.scripts import checkwatches
from lp.testing import TestCaseWithFactory


def fudged_get_external_bugtracker(bugtracker):
    """A version of get_external_bugtracker that returns BugzillaAPI."""
    return BugzillaAPI(bugtracker.baseurl)


class TestCheckwatchesWithSyncableGnomeProducts(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCheckwatchesWithSyncableGnomeProducts, self).setUp()

        # We monkey-patch externalbugtracker.get_external_bugtracker()
        # so that it always returns what we want.
        self.original_get_external_bug_tracker = (
            checkwatches.externalbugtracker.get_external_bugtracker)
        checkwatches.externalbugtracker.get_external_bugtracker = (
            fudged_get_external_bugtracker)

        # Create an updater with a limited set of syncable gnome
        # products.
        self.updater = checkwatches.BugWatchUpdater(
            transaction, QuietFakeLogger(), ['test-product'])

    def tearDown(self):
        checkwatches.externalbugtracker.get_external_bugtracker = (
            self.original_get_external_bug_tracker)
        super(TestCheckwatchesWithSyncableGnomeProducts, self).tearDown()

    def test_bug_496988(self):
        # Regression test for bug 496988. KeyErrors when looking for the
        # remote product for a given bug shouldn't travel upwards and
        # cause the script to abort.
        gnome_bugzilla = getUtility(ILaunchpadCelebrities).gnome_bugzilla
        bug_watch_1 = self.factory.makeBugWatch(
            remote_bug=1, bugtracker=gnome_bugzilla)
        bug_watch_2 = self.factory.makeBugWatch(
            remote_bug=2, bugtracker=gnome_bugzilla)

        # Calling this method shouldn't raise a KeyError, even though
        # there's no bug 2 on the bug tracker that we pass to it.
        self.updater._getExternalBugTrackersAndWatches(
            gnome_bugzilla, [bug_watch_1, bug_watch_2])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
