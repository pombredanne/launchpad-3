# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll interface tests."""

__metaclass__ = type

from zope.component import adaptedBy
from zope.interface import Interface

from lp.services.longpoll.interfaces import (
    ILongPollEvent,
    long_poll_event,
    )
from lp.testing import TestCase


class IEventSourceInterface(Interface):
    """Test interface for an event source."""


class IEventSpecifierInterface(Interface):
    """Test interface for an event specifier."""


class TestLongPollInterfaces(TestCase):

    def test_long_poll_event(self):
        # long_poll_event is a class decorator that declares a class as an
        # ILongPollEvent.
        @long_poll_event(IEventSourceInterface, IEventSpecifierInterface)
        class Something:
            """An example event source."""
        self.assertTrue(ILongPollEvent.implementedBy(Something))
        self.assertEqual(
            (IEventSourceInterface, IEventSpecifierInterface),
            adaptedBy(Something))

    def test_long_poll_event_default(self):
        # By default, long_poll_event assumes that the event spec is
        # basestring.
        @long_poll_event(IEventSourceInterface)
        class Something:
            """An example event source."""
        self.assertTrue(ILongPollEvent.implementedBy(Something))
        self.assertEqual(
            (IEventSourceInterface, basestring),
            adaptedBy(Something))
