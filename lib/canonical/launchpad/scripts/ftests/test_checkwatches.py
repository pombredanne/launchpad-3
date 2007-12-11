# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the checkwatches remote bug synchronisation code."""

__metaclass__ = type
__all__ = []

from unittest import TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests import login
from canonical.launchpad.ftests.externalbugtracker import new_bugtracker
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import (BugTaskStatus, BugTrackerType,
    IBugSet, IBugTaskSet, IPersonSet, IProductSet, IQuestionSet)

class TestCheckwatches(LaunchpadZopelessTestCase):
    """Tests for the bugwatch updating system."""

    def setUp(self):
        """Set up bugs, watches and questions to test with."""
        super(TestCheckwatches, self).setUp()

        # For test_can_update_bug_with_questions we need a bug that has
        # a question linked to it.
        bug_with_question = getUtility(IBugSet).get(10)
        question = getUtility(IQuestionSet).get(1)

        # To link the bug to a question we need to login(). This is
        # because making this link grants karma to the Person who does
        # it.
        login('test@canonical.com')
        question.linkBug(bug_with_question)
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
            bugtracker, 1, sample_person)
        self.bugtask_with_question.bugwatch = self.bugwatch_with_question
        commit()

    def test_can_update_bug_with_questions(self):
        """Test whether bugs with linked questions can be updated."""
        # We need to check that the bug task we created in setUp() is
        # still being referenced by our bug watch.
        self.assertEqual(self.bugwatch_with_question.bugtasks[0].id,
            self.bugtask_with_question.id)

        # We can now update the bug watch, which will in turn update the
        # bug task.
        self.bugwatch_with_question.updateStatus('some status',
            BugTaskStatus.INPROGRESS)
        self.assertEqual(self.bugwatch_with_question.bugtasks[0].status,
            BugTaskStatus.INPROGRESS,
            "BugTask status is inconsistent. Expected %s but got %s" %
            (BugTaskStatus.INPROGRESS.title,
            self.bugtask_with_question.status.title))

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
