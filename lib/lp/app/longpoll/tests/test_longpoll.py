# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.app.longpoll."""

__metaclass__ = type

from zope.component import adapts
from zope.interface import (
    Attribute,
    implements,
    Interface,
    )

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.longpoll import (
    emit,
    subscribe,
    )
from lp.services.longpoll.interfaces import (
    ILongPollEvent,
    ILongPollSubscriber,
    )
from lp.services.messaging.queue import (
    RabbitQueue,
    RabbitRoutingKey,
    )
from lp.testing import TestCase
from lp.testing.fixture import ZopeAdapterFixture


class IFakeObject(Interface):

    ident = Attribute("ident")


class FakeObject:

    implements(IFakeObject)

    def __init__(self, ident):
        self.ident = ident


class FakeEvent:

    adapts(IFakeObject, Interface)
    implements(ILongPollEvent)

    def __init__(self, source, event):
        self.source = source
        self.event = event

    @property
    def event_key(self):
        return "event-key-%s-%s" % (
            self.source.ident, self.event)

    def emit(self, data):
        # Don't cargo-cult this; see .adapters.event.LongPollEvent instead.
        RabbitRoutingKey(self.event_key).send_now(data)


class TestFunctions(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_subscribe(self):
        # subscribe() gets the ILongPollEvent for the given (target, event)
        # and the ILongPollSubscriber for the given request (or the current
        # request is discovered). It subscribes the latter to the event, then
        # returns the event.
        request = LaunchpadTestRequest()
        an_object = FakeObject(12345)
        with ZopeAdapterFixture(FakeEvent):
            event = subscribe(an_object, "foo", request=request)
        self.assertIsInstance(event, FakeEvent)
        self.assertEqual("event-key-12345-foo", event.event_key)
        # Emitting an event-key-12345-foo event will put something on the
        # subscriber's queue.
        event_data = {"1234": 5678}
        event.emit(event_data)
        subscriber = ILongPollSubscriber(request)
        subscribe_queue = RabbitQueue(subscriber.subscribe_key)
        message = subscribe_queue.receive(timeout=5)
        self.assertEqual(event_data, message)

    def test_emit(self):
        # subscribe() gets the ILongPollEvent for the given (target, event)
        # and passes the given data to its emit() method. It then returns the
        # event.
        an_object = FakeObject(12345)
        with ZopeAdapterFixture(FakeEvent):
            event = emit(an_object, "bar", {})
            routing_key = RabbitRoutingKey(event.event_key)
            subscribe_queue = RabbitQueue("whatever")
            routing_key.associateConsumer(subscribe_queue)
            # Emit the event again; the subscribe queue was not associated
            # with the event before now.
            event_data = {"8765": 4321}
            event = emit(an_object, "bar", event_data)
        message = subscribe_queue.receive(timeout=5)
        self.assertEqual(event_data, message)
