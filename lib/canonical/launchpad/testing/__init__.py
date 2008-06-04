# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401,C0301

import unittest

import zope.event
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing.factory import *


class TestCase(unittest.TestCase):
    """Provide Launchpad-specific test facilities."""

    def assertNotifies(self, event_type, callable_obj, *args, **kwargs):
        """Assert that a callable performs a given notification.

        :param event_type: The type of event that notification is expected
            for.
        :param callable_obj: The callable to call.
        :param *args: The arguments to pass to the callable.
        :param **kwargs: The keyword arguments to pass to the callable.
        :return: (result, event), where result was the return value of the
            callable, and event is the event emitted by the callable.
        """
        result, events = capture_events(callable_obj, *args, **kwargs)
        if len(events) == 0:
            raise AssertionError('No notification was performed.')
        elif len(events) > 1:
            raise AssertionError('Too many (%d) notifications performed.'
                % len(events))
        elif not isinstance(events[0], event_type):
            raise AssertionError('Wrong event type: %r (expected %r).' %
                (events[0], event_type))
        return result, events[0]

    def assertSqlAttributeEqualsDate(self, sql_object, attribute_name, date):
        """Fail unless the value of the attribute is equal to the date.

        Use this method to test that date value that may be UTC_NOW is equal
        to another date value. Trickery is required because SQLBuilder truth
        semantics cause UTC_NOW to appear equal to all dates.

        :param sql_object: a security-proxied SQLObject instance.
        :param attribute_name: the name of a database column in the table
            associated to this object.
        :param date: `datetime.datetime` object or `UTC_NOW`.
        """
        # XXX Probably does not belong here, but better location not clear.
        # Used primarily for testing ORM objects, which ought to use factory.
        sql_object = removeSecurityProxy(sql_object)
        sql_object.syncUpdate()
        sql_class = type(sql_object)
        found_object = sql_class.selectOne(
            ('id=%s AND ' + attribute_name + '=%s')
            % sqlvalues(sql_object.id, date))
        if found_object is None:
            self.fail(
                "Expected %s to be %s, but it was %s."
                % (attribute_name, date, getattr(sql_object, attribute_name)))


class TestCaseWithFactory(TestCase):

    def setUp(self, user=ANONYMOUS):
        login(user)
        self.factory = LaunchpadObjectFactory()

    def tearDown(self):
        logout()


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
