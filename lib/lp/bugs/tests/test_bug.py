# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.model.Bug."""

__metaclass__ = type

from lazr.lifecycle.snapshot import Snapshot
from zope.interface import providedBy

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.enum import BugNotificationLevel
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )


class TestBugSubscriptionMethods(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionMethods, self).setUp()
        self.bug = self.factory.makeBug()
        self.person = self.factory.makePerson()

    def test_is_muted_returns_true_for_muted_users(self):
        # Bug.isMuted() will return True if the passed to it has a
        # BugSubscription with a BugNotificationLevel of NOTHING.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(
                self.person, self.person, level=BugNotificationLevel.NOTHING)
            self.assertEqual(True, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_direct_subscribers(self):
        # Bug.isMuted() will return False if the user has a subscription
        # with BugNotificationLevel that's not NOTHING.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(
                self.person, self.person, level=BugNotificationLevel.METADATA)
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_non_subscribers(self):
        # Bug.isMuted() will return False if the user has no
        # subscription.
        with person_logged_in(self.person):
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_mute_mutes_user(self):
        # Bug.mute() adds a muted subscription for the user passed to
        # it.
        with person_logged_in(self.person):
            muted_subscription = self.bug.mute(
                self.person, self.person)
            self.assertEqual(
                BugNotificationLevel.NOTHING,
                muted_subscription.bug_notification_level)

    def test_mute_mutes_muter(self):
        # When exposed in the web API, the mute method regards the
        # first, `person` argument as optional, and the second
        # `muted_by` argument is supplied from the request.  In this
        # case, the person should be the muter.
        with person_logged_in(self.person):
            self.bug.mute(None, self.person)
            self.assertTrue(self.bug.isMuted(self.person))

    def test_mute_mutes_user_with_existing_subscription(self):
        # Bug.mute() will update an existing subscription so that it
        # becomes muted.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(self.person, self.person)
            muted_subscription = self.bug.mute(self.person, self.person)
            self.assertEqual(subscription, muted_subscription)
            self.assertEqual(
                BugNotificationLevel.NOTHING,
                subscription.bug_notification_level)

    def test_unmute_unmutes_user(self):
        # Bug.unmute() will remove a muted subscription for the user
        # passed to it.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.assertTrue(self.bug.isMuted(self.person))
            self.bug.unmute(self.person, self.person)
            self.assertFalse(self.bug.isMuted(self.person))

    def test_unmute_mutes_unmuter(self):
        # When exposed in the web API, the unmute method regards the
        # first, `person` argument as optional, and the second
        # `unmuted_by` argument is supplied from the request.  In this
        # case, the person should be the muter.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.bug.unmute(None, self.person)
            self.assertFalse(self.bug.isMuted(self.person))


class TestBugSnapshotting(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSnapshotting, self).setUp()
        self.bug = self.factory.makeBug()
        self.person = self.factory.makePerson()

    def test_bug_snapshot_does_not_include_messages(self):
        # A snapshot of a bug does not include its messages or
        # attachments (which get the messages from the database).  If it
        # does, the webservice can become unusable if changes are made
        # to bugs with many comments, such as bug 1. See, for instance,
        # bug 744888.  This test is primarily to keep the problem from
        # slipping in again.  To do so, we resort to somewhat
        # extraordinary measures.  In addition to verifying that the
        # snapshot does not have the attributes that currently trigger
        # the problem, we also actually look at the SQL that is
        # generated by creating the snapshot.  With this, we can verify
        # that the Message table is not included.  This is ugly, but
        # this has a chance of fighting against future eager loading
        # optimizations that might trigger the problem again.
        with person_logged_in(self.person):
            with StormStatementRecorder() as recorder:
                snapshot = Snapshot(self.bug, providing=providedBy(self.bug))
            sql_statements = recorder.statements
        # This uses "self" as a marker to show that the attribute does not
        # exist.  We do not use hasattr because it eats exceptions.
        #self.assertTrue(getattr(snapshot, 'messages', self) is self)
        #self.assertTrue(getattr(snapshot, 'attachments', self) is self)
        for sql in sql_statements:
            # We are going to be aggressive about looking for the problem in
            # the SQL.  We'll split the SQL up by whitespace, and then look
            # for strings that start with "message".  If that is too
            # aggressive in the future from some reason, please do adjust the
            # test appropriately.
            sql_tokens = sql.lower().split()
            self.assertEqual(
                [token for token in sql_tokens
                 if token.startswith('message')],
                [])
