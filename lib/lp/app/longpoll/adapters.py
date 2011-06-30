# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = []


from uuid import uuid4

from .interfaces import ILongPollSubscriber
from lazr.restful.interfaces import IJSONRequestCache
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import IApplicationRequest


class LongPollSubscriber:

    adapts(IApplicationRequest)
    implements(ILongPollSubscriber)

    def __init__(self, request):
        self.request = request
        cache = IJSONRequestCache(request)
        if "longpoll" not in cache.objects:
            cache.objects["longpoll"] = {
                "key": str(uuid4()),
                "subscriptions": [],
                }

    @property
    def subscribe_key(self):
        cache = IJSONRequestCache(self.request)
        return cache.objects["longpoll"]["key"]

    def subscribe(self, emitter):
        cache = IJSONRequestCache(self.request)
        cache.objects["longpoll"]["subscriptions"].append(emitter.emit_key)
