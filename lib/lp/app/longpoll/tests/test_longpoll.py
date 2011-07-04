# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll subscriber adapter tests."""

__metaclass__ = type

from fixtures import Fixture
from lazr.restful.interfaces import IJSONRequestCache
from zope.component import (
    adapts,
    getSiteManager,
    )
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
from lp.app.longpoll.interfaces import ILongPollEvent
from lp.testing import TestCase
from lp.testing.matchers import Contains


class IFakeObject(Interface):
    """A marker interface."""

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


class AdapterFixture(Fixture):

    def __init__(self, *args, **kwargs):
        self._args, self._kwargs = args, kwargs

    def setUp(self):
        super(AdapterFixture, self).setUp()
        site_manager = getSiteManager()
        site_manager.registerAdapter(
            *self._args, **self._kwargs)
        self.addCleanup(
            site_manager.unregisterAdapter,
            *self._args, **self._kwargs)


class TestSubscribe(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_subscribe(self):
        request = LaunchpadTestRequest()
        cache = IJSONRequestCache(request)
        an_object = FakeObject(12345)
        with AdapterFixture(FakeEvent):
            event = subscribe(an_object, "foo", request=request)
        self.assertIsInstance(event, FakeEvent)
        self.assertEqual("event-key-12345-foo", event.event_key)
        self.assertThat(
            cache.objects["longpoll"]["subscriptions"],
            Contains("event-key-12345-foo"))
        # TODO: Send a message to the subscriber.


class TestEmit(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_emit(self):
        # TODO
        emit
