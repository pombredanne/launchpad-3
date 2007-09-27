# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Launchpad/Mailman doctests."""

import time
import doctest
import datetime
import unittest

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests import xmlrpc_helper
from canonical.launchpad.interfaces import (
    IMailingListSet, IPersonSet, MailingListStatus)
from canonical.launchpad.mailman import runmailman
from canonical.testing import LaunchpadFunctionalLayer
from canonical.testing.profiled import profiled
from zope.component import getUtility


class MailmanLayer(LaunchpadFunctionalLayer):
    @classmethod
    @profiled
    def setUp(cls):
        # Don't register the atexit handler because our tearDown will
        # explicitly shut Mailman down.
        runmailman.start_mailman()

    @classmethod
    @profiled
    def tearDown(cls):
        runmailman.stop_mailman()


class TestMailmanXMLRPC(unittest.TestCase):
    layer = MailmanLayer

    def test_createList(self):
        """Test that Mailman will create approved lists."""
        login(ANONYMOUS)
        # Create two teams and a list for each team.
        team_one = xmlrpc_helper.mailingListNewTeam('team-one')
        list_one = getUtility(IMailingListSet).new(team_one)
        # Review the list, which approves it.
        carlos = getUtility(IPersonSet).getByName('carlos')
        list_one.review(carlos, MailingListStatus.APPROVED)
        flush_database_updates()
        # Now poll every 1/2 second until the mailing list status changes,
        # then check to ensure that Mailman actually created the mailing
        # lists.  Wait no longer than 5 seconds.
        until = datetime.datetime.now() + datetime.timedelta(seconds=500)
        while datetime.datetime.now() < until:
            flush_database_updates()
            if list_one.status == MailingListStatus.ACTIVE:
                break
            time.sleep(0.5)
        self.assertEqual(list_one.status, MailingListStatus.ACTIVE)


def test_suite():
    suite = unittest.TestSuite()

    # If Mailman isn't even configured to be built, then there's really
    # nothing we can do.  This isn't completely correct because it doesn't
    # catch the case where Mailman was built, but then the 'build' key was set
    # back to false.  This is really better than testing to see if the Mailman
    # package is importable because, that we really want to do in the doctest!
    from canonical.config import config
    if not config.mailman.build.build:
        return suite

    # These tests will only be run when Mailman is enabled.
    test = doctest.DocFileSuite(
        'test-lpmm.txt',
        optionflags = (doctest.ELLIPSIS     |
                       doctest.REPORT_NDIFF |
                       doctest.NORMALIZE_WHITESPACE),
        )
    suite.addTest(test)
    suite.addTest(unittest.makeSuite(TestMailmanXMLRPC))
    return suite
