# Copyright 2011-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugNotificationBuilder email construction."""

from datetime import datetime

import pytz
from zope.security.interfaces import Unauthorized

from lp.bugs.mail.bugnotificationbuilder import BugNotificationBuilder
from lp.registry.enums import PersonVisibility
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestBugNotificationBuilder(TestCaseWithFactory):
    """Test emails sent when subscribed by someone else."""

    layer = DatabaseFunctionalLayer

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
        with person_logged_in(self.bug.owner):
            self.bug.owner.expanded_notification_footers = True
        message = self.builder.build(
            'from', self.bug.owner, 'body', 'subject', utc_now, filters=[])
        self.assertIn(
            "\n-- \nLaunchpad-Notification-Type: bug\n",
            message.get_payload(decode=True))

    def test_private_team(self):
        # Recipients can be invisible private teams, as
        # BugNotificationBuilder runs in the context of the user making
        # the change. They work fine.
        private_team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE, email="private@example.com")
        random = self.factory.makePerson()
        with person_logged_in(random):
            self.assertRaises(
                Unauthorized, getattr, private_team,
                'expanded_notification_footers')
            utc_now = datetime.now(pytz.UTC)
            message = self.builder.build(
                'from', private_team, 'body', 'subject', utc_now, filters=[])
        self.assertIn("private@example.com", str(message))
