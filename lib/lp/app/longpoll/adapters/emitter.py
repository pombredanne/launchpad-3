# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = [
    "LongPollEmitter",
    ]

from lp.services.messaging.queue import RabbitRoutingKey


class LongPollEmitter:
    """Base-class for emitter adapters."""

    #adapts(Interface, Interface)
    #implements(ILongPollEmitter)

    def __init__(self, source, event):
        self.source = source
        self.event = event

    @property
    def emit_key(self):
        raise NotImplementedError(self.__class__.emit_key)

    def emit(self, data):
        routing_key = RabbitRoutingKey(self.emit_key)
        routing_key.send(data)
