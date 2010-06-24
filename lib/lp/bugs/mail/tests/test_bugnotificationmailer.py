# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `BugNotificationMailer` code."""

__metaclass__ = type

import unittest

from lp.bugs.mail.bugnotificationmailer import BugNotificationMailer
from lp.testing import TestCaseWithFactory


class BugNotificationMailerTestCase(TestCaseWithFactory):
    """Tests for the BugNotificationMailer class."""

    def setUp(self):
        super(BugNotificationMailer, self).setup()

        self.notification_recipient = self.factory.makePerson()
        self.bug = self.factory.makeBug()

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
