# Copyright 2009 Canonical Ltd.  All rights reserved.

import unittest
from datetime import datetime, timedelta

import pytz

from canonical.launchpad.ftests import login
from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestPoll(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def test_getWinners_handle_polls_with_only_spoilt_votes(self):
        login('mark@hbd.com')
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner)
        poll = self.factory.makePoll(team, 'name', 'title', 'proposition')
        # Force opening of poll so that we can vote.
        poll.dateopens = datetime.now(pytz.UTC) - timedelta(minutes=2)
        poll.storeSimpleVote(owner, None)
        # Force closing of the poll so that we can call getWinners().
        poll.datecloses = datetime.now(pytz.UTC)
        self.failUnless(poll.getWinners() is None, poll.getWinners())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
