# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = [
    "generate_subscribe_key",
    "LongPollApplicationRequestSubscriber",
    ]

from uuid import uuid4

from lazr.restful.interfaces import IJSONRequestCache
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import IApplicationRequest

from lp.services.longpoll.interfaces import ILongPollSubscriber
from lp.services.messaging.queue import (
    RabbitQueue,
    RabbitRoutingKey,
    )


def generate_subscribe_key():
    """Generate a suitable new, unique, subscribe key."""
    return "longpoll.subscribe.%s" % uuid4()


class LongPollApplicationRequestSubscriber:

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

    def subscribe(self, event):
        cache = IJSONRequestCache(self.request)
        if "longpoll" not in cache.objects:
            cache.objects["longpoll"] = {
                "key": generate_subscribe_key(),
                "subscriptions": [],
                }
        subscribe_queue = RabbitQueue(self.subscribe_key)
        routing_key = RabbitRoutingKey(event.event_key)
        routing_key.associateConsumer(subscribe_queue)
        cache.objects["longpoll"]["subscriptions"].append(event.event_key)
