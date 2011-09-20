# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = [
    "generate_event_key",
    "LongPollEvent",
    ]

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
