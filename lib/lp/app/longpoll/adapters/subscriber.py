# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = []

from uuid import uuid4

from lazr.restful.interfaces import IJSONRequestCache
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import IApplicationRequest

from lp.app.longpoll.interfaces import ILongPollSubscriber
from lp.services.messaging.queue import (
    RabbitQueue,
    RabbitRoutingKey,
    )


class LongPollSubscriber:

    adapts(IApplicationRequest)
    implements(ILongPollSubscriber)

    def __init__(self, request):
        self.request = request

    @property
    def subscribe_key(self):
        objects = IJSONRequestCache(self.request).objects
        if "longpoll" in objects:
            return objects["longpoll"]["key"]
        return None

    def subscribe(self, emitter):
        cache = IJSONRequestCache(self.request)
        if "longpoll" not in cache.objects:
            cache.objects["longpoll"] = {
                # TODO: Add something descriptive into the key.
                "key": str(uuid4()),
                "subscriptions": [],
                }
        subscribe_queue = RabbitQueue(self.subscribe_key)
        routing_key = RabbitRoutingKey(emitter.emit_key)
        routing_key.associateConsumer(subscribe_queue)
        cache.objects["longpoll"]["subscriptions"].append(emitter.emit_key)
