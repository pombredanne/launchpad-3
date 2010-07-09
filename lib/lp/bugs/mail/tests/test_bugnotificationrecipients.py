# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugnotificationrecipients module."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.bugs.mail.bugnotificationrecipients import (
    BugNotificationRecipientReason)
from lp.testing import TestCaseWithFactory


class BugNotificationRecipientReasonTestCase(TestCaseWithFactory):
    """A TestCase for the `BugNotificationRecipientReason` class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BugNotificationRecipientReasonTestCase, self).setUp()
        self.person = self.factory.makePerson()

    def test_forDupeSubscriber(self):
        # BugNotificationRecipientReason.forDupeSubscriber() will return
        # a BugNotificationRecipientReason with headers appropriate for
        # a subscriber via a duplicate bug.
        duplicate_bug = self.factory.makeBug()
        reason = BugNotificationRecipientReason.forDupeSubscriber(
            self.person, duplicate_bug)

        expected_header = (
            'Subscriber of Duplicate via Bug %s' % duplicate_bug.id)
        expected_reason = (
            'You received this bug notification because you are a direct '
            'subscriber of duplicate bug %s.' % duplicate_bug.id)
        self.assertEqual(expected_header, reason.mail_header)
        self.assertEqual(expected_reason, reason.getReason())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
