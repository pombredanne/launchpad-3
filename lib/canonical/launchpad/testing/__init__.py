# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401,C0301

from unittest import TestCase

from canonical.database.sqlbase import cursor
import zope.event

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing.factory import *


class TestCaseWithFactory(TestCase):

    def setUp(self):
        login(ANONYMOUS)
        self.factory = LaunchpadObjectFactory()

    def tearDown(self):
        logout()

    def assertIsDBNow(self, value):
        """Assert supplied value equals database time.

        The database time is the same for the whole transaction, and may
        not match the current time exactly.
        :param value: A datetime that is expected to match the current
            database time.
        """
        # XXX Probably does not belong here, but better location not clear.
        # Used primarily for testing ORM objects, which ought to use factory.
        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';")
        [database_now] = cur.fetchone()
        self.assertEqual(
            database_now.utctimetuple(), value.utctimetuple())


def capture_events(callable_obj, *args, **kwargs):
    """Capture the events emitted by a callable.

    :param event_type: The type of event that notification is expected
        for.
    :param callable_obj: The callable to call.
    :param *args: The arguments to pass to the callable.
    :param **kwargs: The keyword arguments to pass to the callable.
    :return: (result, events), where result was the return value of the
        callable, and events are the events emitted by the callable.
    """
    events = []
    def on_notify(event):
        events.append(event)
    old_subscribers = zope.event.subscribers[:]
    try:
        zope.event.subscribers[:] = [on_notify]
        result = callable_obj(*args, **kwargs)
        return result, events
    finally:
        zope.event.subscribers[:] = old_subscribers
