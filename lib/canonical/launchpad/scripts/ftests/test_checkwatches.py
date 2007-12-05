# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the checkwatches remote bug synchronisation code."""

__metaclass__ = type
__all__ = []

from unittest import TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import IBugSet

class TestCheckwatches(LaunchpadZopelessTestCase):
    """Tests for the bugwatch updating system."""

    dbuser = config.malone.bugnotification_dbuser

    def setUp(self):
        """Set up bugs, watches and questions to test with."""
        super(TestCheckwatches, self).setUp()

        self.bug = getUtility(IBugSet).get(10)
        self.bugwatch = self.bug


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
