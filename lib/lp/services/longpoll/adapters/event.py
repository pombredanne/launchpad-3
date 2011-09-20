# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = [
    "generate_event_key",
    "LongPollEvent",
    ]

from zope.component import (
    adapter,
    queryMultiAdapter,
    )
from zope.component.interfaces import IObjectEvent

from lp.services.longpoll.interfaces import ILongPollEvent
from lp.services.messaging.queue import RabbitRoutingKey


router_factory = RabbitRoutingKey


def generate_event_key(*components):
    """Generate a suitable event name."""
    if len(components) == 0:
        raise AssertionError(
            "Event keys must contain at least one component.")
    return "longpoll.event.%s" % ".".join(
        str(component) for component in components)


class LongPollEvent:
    """Base-class for event adapters.

    Sub-classes need to declare something along the lines of:

        adapts(Interface, Interface)
        implements(ILongPollEvent)

    """

    def __init__(self, source, event):
        self.source = source
        self.event = event

    @property
    def event_key(self):
        """See `ILongPollEvent`."""
        raise NotImplementedError(self.__class__.event_key)

    def emit(self, data):
        """See `ILongPollEvent`."""
        payload = {"event_key": self.event_key, "event_data": data}
        router = router_factory(self.event_key)
        router.send(payload)


@adapter(IObjectEvent)
def object_event(object_event):
    """A subscription handler for `IObjectEvent` events.

    This forms a bridge from `zope.event` style `notify()` events using
    `IObjectEvent`s, `lazr.lifecycle` for example.

    This looks for an adapter from `(object_event.object, object_event)` to
    `ILongPollEvent`. If one exists, its `emit()` method is called with
    `object_event` as the sole argument.
    """
    longpoll_event = queryMultiAdapter(
        (object_event.object, object_event), ILongPollEvent)
    if longpoll_event is not None:
        longpoll_event.emit(object_event)
