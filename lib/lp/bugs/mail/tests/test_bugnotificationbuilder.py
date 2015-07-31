# Copyright 2011-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugNotificationBuilder email construction."""

from datetime import datetime

import pytz

from lp.bugs.mail.bugnotificationbuilder import BugNotificationBuilder
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer


class TestBugNotificationBuilder(TestCaseWithFactory):
    """Test emails sent when subscribed by someone else."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Run the tests as a logged-in user.
        super(TestBugNotificationBuilder, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.builder = BugNotificationBuilder(self.bug)

    def test_build_filters_empty(self):
        """Filters are added."""
        utc_now = datetime.now(pytz.UTC)
        message = self.builder.build('from', self.bug.owner, 'body', 'subject',
                                     utc_now, filters=[])
        self.assertIs(None,
                      message.get("X-Launchpad-Subscription", None))

    def test_build_filters_single(self):
        """Filters are added."""
        utc_now = datetime.now(pytz.UTC)
        message = self.builder.build('from', self.bug.owner, 'body', 'subject',
                                     utc_now, filters=[u"Testing filter"])
        self.assertContentEqual(
            [u"Testing filter"],
            message.get_all("X-Launchpad-Subscription"))

    def test_build_filters_multiple(self):
        """Filters are added."""
        utc_now = datetime.now(pytz.UTC)
        message = self.builder.build(
            'from', self.bug.owner, 'body', 'subject', utc_now,
            filters=[u"Testing filter", u"Second testing filter"])
        self.assertContentEqual(
            [u"Testing filter", u"Second testing filter"],
            message.get_all("X-Launchpad-Subscription"))

    def test_mails_contain_notification_type_header(self):
        utc_now = datetime.now(pytz.UTC)
        message = self.builder.build(
            'from', self.bug.owner, 'body', 'subject', utc_now, filters=[])
        self.assertEqual(
            "bug", message.get("X-Launchpad-Notification-Type", None))

    def test_mails_no_expanded_footer(self):
        # Recipients without expanded_notification_footers do not receive an
        # expanded footer on messages.
        utc_now = datetime.now(pytz.UTC)
        message = self.builder.build(
            'from', self.bug.owner, 'body', 'subject', utc_now, filters=[])
        self.assertNotIn(
            "Launchpad-Notification-Type", message.get_payload(decode=True))

    def test_mails_append_expanded_footer(self):
        # Recipients with expanded_notification_footers receive an expanded
        # footer on messages.
        utc_now = datetime.now(pytz.UTC)
        self.bug.owner.expanded_notification_footers = True
        message = self.builder.build(
            'from', self.bug.owner, 'body', 'subject', utc_now, filters=[])
        self.assertIn(
            "\n-- \nLaunchpad-Notification-Type: bug\n",
            message.get_payload(decode=True))
