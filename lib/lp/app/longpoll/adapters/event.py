# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = [
    "LongPollEvent",
    ]

from lp.services.messaging.queue import RabbitRoutingKey


class LongPollEvent:
    """Base-class for event adapters."""

    #adapts(Interface, Interface)
    #implements(ILongPollEvent)

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
        routing_key = RabbitRoutingKey(self.event_key)
        routing_key.send(payload)
