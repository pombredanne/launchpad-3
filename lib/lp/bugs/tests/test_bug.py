# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.model.Bug."""

__metaclass__ = type

from lazr.lifecycle.snapshot import Snapshot
from zope.interface import providedBy

from canonical.launchpad.webapp.adapter import (
    get_request_statements,
    set_request_started,
    clear_request_started,
    )
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.enum import BugNotificationLevel
from lp.testing import (
    person_logged_in,
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
            # We need to do this to enable SQL logging.
            set_request_started(enable_timeout=False)
            try:
                snapshot = Snapshot(self.bug, providing=providedBy(self.bug))
                sql_statements = get_request_statements()
            finally:
                clear_request_started()
        # This uses "self" as a marker to show that the attribute does not
        # exist.  We do not use hasattr because it eats exceptions.
        self.assertTrue(getattr(snapshot, 'messages', self) is self)
        self.assertTrue(getattr(snapshot, 'attachments', self) is self)
        for (start, stop, dbname, sql) in sql_statements:
            # Yes, we are doing dumb parsing of SQL.  Hopefully this is not
            # too fragile.  See comment at start of test for why we are
            # doing this bizarre thing.
            # This gets the string between "SELECT" and "FROM".  It should
            # handle "WITH" being used.  We use the SELECT phrase rather than
            # the FROM phrase because the FROM might be a subquery, and this
            # seemed simpler.
            sql = sql.lower()
            select_sql = sql.partition('select ')[2].partition(' from ')[0]
            # This gets the field names with a simple split.
            select_fields = select_sql.split(', ')
            # Now we verify that the Message table is not referenced.
            # Of course, if the Message table is aliased, it won't catch
            # it.  This shouldn't be a common problem for the way we
            # currently generate our SQL, and for the kind of problem we are
            # trying to prevent (that is, getting 1001 messages for a
            # bug snapshot).
            self.assertEqual(
                [field_name for field_name in select_fields
                 if field_name.startswith('message.')],
                [])
