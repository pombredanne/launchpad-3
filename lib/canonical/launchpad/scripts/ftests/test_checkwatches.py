# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the checkwatches remote bug synchronisation code."""

__metaclass__ = type
__all__ = []

from unittest import TestLoader

from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.database.sqlbase import commit, flush_database_updates
from canonical.launchpad.ftests import login
from canonical.launchpad.ftests.externalbugtracker import (new_bugtracker,
    TestRoundup)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import (BugTaskStatus, BugTrackerType,
    IBugSet, IBugTaskSet, ILanguageSet, IPersonSet, IProductSet,
    IQuestionSet)

class TestCheckwatches(LaunchpadZopelessTestCase):
    """Tests for the bugwatch updating system."""

    dbuser = config.checkwatches.dbuser

    def setUp(self):
        """Set up bugs, watches and questions to test with."""
        super(TestCheckwatches, self).setUp()

        # For test_can_update_bug_with_questions we need a bug that has
        # a question linked to it.
        self.bug = getUtility(IBugSet).get(10)
        self.question = getUtility(IQuestionSet).get(1)

        login('test@canonical.com')
        self.questionbug = self.question.linkBug(self.bug)
        commit()

        # For test_can_update_bug_with_questions we also need a bug
        # watch and by extension a bug tracker.
        self.sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        self.bugtracker = new_bugtracker(BugTrackerType.ROUNDUP)
        self.bugtask = getUtility(IBugTaskSet).createTask(self.bug,
            self.sample_person, product=getUtility(IProductSet).getByName(
            'firefox'))
        self.bugwatch = self.bug.addWatch(self.bugtracker, 1,
            self.sample_person)
        self.bugtask.bugwatch = self.bugwatch
        commit()

    def test_can_update_bug_with_questions(self):
        """Test whether bugs with linked questions can be updated."""
        # We need to check that the bug task we created in setUp() is
        # still being referenced by our bug watch.
        self.assertEqual(self.bugwatch.bugtasks[0].id, self.bugtask.id)

        # We can now update the bug watch, which will in turn update the
        # bug task.
        self.bugwatch.updateStatus('some status', BugTaskStatus.INPROGRESS)
        self.assertEqual(self.bugwatch.bugtasks[0].status,
            BugTaskStatus.INPROGRESS,
            "BugTask status is inconsistent. Expected %s but got %s" %
            (BugTaskStatus.INPROGRESS.title, self.bugtask.status.title))

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
