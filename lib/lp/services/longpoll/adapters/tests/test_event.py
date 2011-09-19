# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll event adapter tests."""

__metaclass__ = type

from lazr.lifecycle.event import ObjectCreatedEvent
from zope.component import adapts
from zope.component.interfaces import IObjectEvent
from zope.event import notify
from zope.interface import implements

from canonical.testing.layers import (
    BaseLayer,
    LaunchpadFunctionalLayer,
    )
from lp.services.longpoll.adapters.event import (
    generate_event_key,
    LongPollEvent,
    )
from lp.services.longpoll.interfaces import ILongPollEvent
from lp.services.longpoll.testing import (
    capture_longpoll_emissions,
    LongPollEventRecord,
    )
from lp.services.messaging.queue import RabbitMessageBase
from lp.testing import TestCase
from lp.testing.fixture import ZopeAdapterFixture
from lp.testing.matchers import Contains


class FakeEvent(LongPollEvent):

    implements(ILongPollEvent)

    @property
    def event_key(self):
        return "event-key-%s-%s" % (self.source, self.event)


class TestLongPollEvent(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_interface(self):
        event = FakeEvent("source", "event")
        self.assertProvides(event, ILongPollEvent)

    def test_event_key(self):
        # event_key is not implemented in LongPollEvent; subclasses must
        # provide it.
        event = LongPollEvent("source", "event")
        self.assertRaises(NotImplementedError, getattr, event, "event_key")

    def test_emit(self):
        # LongPollEvent.emit() sends the given data to `event_key`.
        event = FakeEvent("source", "event")
        event_data = {"hello": 1234}
        event.emit(event_data)
        expected_message = {
            "event_key": event.event_key,
            "event_data": event_data,
            }
        pending_messages = [
            message for (call, message) in
            RabbitMessageBase.class_locals.messages]
        self.assertThat(pending_messages, Contains(expected_message))


class FakeObjectEvent(LongPollEvent):

    adapts(basestring, IObjectEvent)
    implements(ILongPollEvent)

    @property
    def event_key(self):
        return "event-key-%s-created" % self.source

    def emit(self, data):
        super(FakeObjectEvent, self).emit(data.object)


class TestObjectEventBridge(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_object_event_no_adapter(self):
        # When no adapter is registered for the given event, no longpoll
        # emissions are recorded.
        with capture_longpoll_emissions() as log:
            notify(ObjectCreatedEvent("bob"))
        self.assertEqual([], log)

    def test_object_event(self):
        # When an adapter is registered for the given event, a single longpoll
        # emission is recorded.
        self.useFixture(ZopeAdapterFixture(FakeObjectEvent))
        with capture_longpoll_emissions() as log:
            notify(ObjectCreatedEvent("bob"))
        expected = [
            LongPollEventRecord(
                "event-key-bob-created",
                {"event_key": "event-key-bob-created",
                 "event_data": "bob"}),
            ]
        self.assertEqual(expected, log)


class TestFunctions(TestCase):

    layer = BaseLayer

    def test_generate_event_key_no_components(self):
        self.assertRaises(
            AssertionError, generate_event_key)

    def test_generate_event_key(self):
        self.assertEqual(
            "longpoll.event.event-name",
            generate_event_key("event-name"))
        self.assertEqual(
            "longpoll.event.source-name.event-name",
            generate_event_key("source-name", "event-name"))
        self.assertEqual(
            "longpoll.event.type-name.source-name.event-name",
            generate_event_key("type-name", "source-name", "event-name"))

    def test_generate_event_key_stringifies_components(self):
        self.assertEqual(
            "longpoll.event.job.1234.COMPLETED",
            generate_event_key("job", 1234, "COMPLETED"))
