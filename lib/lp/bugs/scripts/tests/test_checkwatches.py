# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Checkwatches unit tests."""

__metaclass__ = type

import unittest
import transaction

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugTrackerType, IBugSet, IBugTaskSet,
    ILaunchpadCelebrities, IPersonSet, IProductSet, IQuestionSet)
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing import LaunchpadZopelessLayer

from lp.bugs.externalbugtracker.bugzilla import BugzillaAPI
from lp.bugs.scripts import checkwatches
from lp.bugs.scripts.checkwatches import CheckWatchesErrorUtility
from lp.bugs.tests.externalbugtracker import (
    TestBugzillaAPIXMLRPCTransport, new_bugtracker)
from lp.testing import TestCaseWithFactory


def always_BugzillaAPI_get_external_bugtracker(bugtracker):
    """A version of get_external_bugtracker that returns BugzillaAPI."""
    return BugzillaAPI(bugtracker.baseurl)


class NonConnectingBugzillaAPI(BugzillaAPI):
    """A non-connected version of the BugzillaAPI ExternalBugTracker."""

    bugs = {
        1: {'product': 'test-product'},
        }

    def getCurrentDBTime(self):
        return None

    def getExternalBugTrackerToUse(self):
        return self

    def getProductsForRemoteBugs(self, remote_bugs):
        """Return the products for some remote bugs.

        This method is basically the same as that of the superclass but
        without the call to initializeRemoteBugDB().
        """
        bug_products = {}
        for bug_id in bug_ids:
            # If one of the bugs we're trying to get the product for
            # doesn't exist, just skip it.
            try:
                actual_bug_id = self._getActualBugId(bug_id)
            except BugNotFound:
                continue

            bug_dict = self._bugs[actual_bug_id]
            bug_products[bug_id] = bug_dict['product']

        return bug_products


class NoBugWatchesByRemoteBugUpdater(checkwatches.BugWatchUpdater):
    """A subclass of BugWatchUpdater with methods overridden for testing."""

    def _getBugWatchesForRemoteBug(self, remote_bug_id, bug_watch_ids):
        """Return an empty list.

        This method overrides _getBugWatchesForRemoteBug() so that bug
        497141 can be regression-tested.
        """
        return []


class TestCheckwatchesWithSyncableGnomeProducts(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCheckwatchesWithSyncableGnomeProducts, self).setUp()

        # We monkey-patch externalbugtracker.get_external_bugtracker()
        # so that it always returns what we want.
        self.original_get_external_bug_tracker = (
            checkwatches.externalbugtracker.get_external_bugtracker)
        checkwatches.externalbugtracker.get_external_bugtracker = (
            always_BugzillaAPI_get_external_bugtracker)

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


class TestBugWatchUpdater(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_bug_497141(self):
        # Regression test for bug 497141. KeyErrors raised in
        # BugWatchUpdater.updateBugWatches() shouldn't cause
        # checkwatches to abort.
        updater = NoBugWatchesByRemoteBugUpdater(
            transaction, QuietFakeLogger())

        # Create a couple of bug watches for testing purposes.
        bug_tracker = self.factory.makeBugTracker()
        bug_watches = [
            self.factory.makeBugWatch(bugtracker=bug_tracker)
            for i in range(2)]

        # Use a test XML-RPC transport to ensure no connections happen.
        test_transport = TestBugzillaAPIXMLRPCTransport(bug_tracker.baseurl)
        remote_system = NonConnectingBugzillaAPI(
            bug_tracker.baseurl, xmlrpc_transport=test_transport)

        # Calling updateBugWatches() shouldn't raise a KeyError, even
        # though with our broken updater _getExternalBugTrackersAndWatches()
        # will return an empty dict.
        updater.updateBugWatches(remote_system, bug_watches)

        # An error will have been logged instead of the KeyError being
        # raised.
        error_utility = CheckWatchesErrorUtility()
        last_oops = error_utility.getLastOopsReport()
        self.assertTrue(
            last_oops.value.startswith('Spurious remote bug ID'))


class TestUpdateBugsWithLinkedQuestions(unittest.TestCase):
    """Tests for updating bugs with linked questions."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up bugs, watches and questions to test with."""
        super(TestUpdateBugsWithLinkedQuestions, self).setUp()

        # For test_can_update_bug_with_questions we need a bug that has
        # a question linked to it.
        bug_with_question = getUtility(IBugSet).get(10)
        question = getUtility(IQuestionSet).get(1)

        # XXX gmb 2007-12-11 bug 175545:
        #     We shouldn't have to login() here, but since
        #     database.buglinktarget.BugLinkTargetMixin.linkBug()
        #     doesn't accept a user parameter, instead depending on the
        #     currently logged in user, we get an exception if we don't.
        login('test@canonical.com')
        question.linkBug(bug_with_question)

        # We subscribe launchpad_developers to the question since this
        # indirectly subscribes foo.bar@canonical.com to it, too. We can
        # then use this to test the updating of a question with indirect
        # subscribers from a bug watch.
        question.subscribe(
            getUtility(ILaunchpadCelebrities).launchpad_developers)
        commit()

        # We now need to switch to the checkwatches DB user so that
        # we're testing with the correct set of permissions.
        self.layer.switchDbUser(config.checkwatches.dbuser)

        # For test_can_update_bug_with_questions we also need a bug
        # watch and by extension a bug tracker.
        sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        bugtracker = new_bugtracker(BugTrackerType.ROUNDUP)
        self.bugtask_with_question = getUtility(IBugTaskSet).createTask(
            bug_with_question, sample_person,
            product=getUtility(IProductSet).getByName('firefox'))
        self.bugwatch_with_question = bug_with_question.addWatch(
            bugtracker, '1', getUtility(ILaunchpadCelebrities).janitor)
        self.bugtask_with_question.bugwatch = self.bugwatch_with_question
        commit()

    def test_can_update_bug_with_questions(self):
        """Test whether bugs with linked questions can be updated.

        This will also test whether indirect subscribers of linked
        questions will be notified of the changes made when the bugwatch
        is updated.
        """
        # We need to check that the bug task we created in setUp() is
        # still being referenced by our bug watch.
        self.assertEqual(self.bugwatch_with_question.bugtasks[0].id,
            self.bugtask_with_question.id)

        # We can now update the bug watch, which will in turn update the
        # bug task and the linked question.
        self.bugwatch_with_question.updateStatus('some status',
            BugTaskStatus.INPROGRESS)
        self.assertEqual(self.bugwatch_with_question.bugtasks[0].status,
            BugTaskStatus.INPROGRESS,
            "BugTask status is inconsistent. Expected %s but got %s" %
            (BugTaskStatus.INPROGRESS.title,
            self.bugtask_with_question.status.title))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
