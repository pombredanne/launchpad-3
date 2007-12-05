# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the checkwatches remote bug synchronisation code."""

__metaclass__ = type
__all__ = []

from unittest import TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests.externalbugtracker import login
from canonical.launchpad.ftests.externalbugtracker import (new_bugtracker,
    TestRoundup)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import (BugTrackerType, IBugSet,
    IPersonSet, IQuestionSet)

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
        self.question.linkBug(self.bug)

        # For test_can_update_bug_with_questions we also need a bug
        # watch and by extension a bug tracker.
        sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        self.bugtracker = new_bugtracker(BugTrackerType.ROUNDUP)
        self.bugwatch = self.bug.addWatch(self.bugtracker, 1,
            sample_person)
        self.external_bugtracker = TestRoundup(self.bugtracker)

    def test_can_update_bug_with_questions(self):
        """Test whether bugs with linked questions can be updated."""
        self.external_bugtracker.updateBugWatches([self.bugwatch])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
