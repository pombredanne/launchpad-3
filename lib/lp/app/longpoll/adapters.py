# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = []


from uuid import uuid4

from .interfaces import (
    ILongPollEmitter,
    ILongPollSubscriber,
    )
from lazr.restful.interfaces import IJSONRequestCache
from lazr.restful.utils import get_current_browser_request
from zope.component import (
    adapts,
    getMultiAdapter,
    )
from zope.interface import (
    implements,
    Interface,
    )
from zope.publisher.interfaces import IApplicationRequest

from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )
from lp.services.messaging.utility import messaging


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
                "key": str(uuid4()),
                "subscriptions": [],
                }
        messaging.listen(self.subscribe_key, emitter.emit_key)
        cache.objects["longpoll"]["subscriptions"].append(emitter.emit_key)


def subscribe(target, event):
    """Convenience method to subscribe the current request.

    :param target: Something that can be adapted to `ILongPollEmitter`.
    :param event: The name of the event to subscribe to.

    :return: The key that has been subscribed to.
    """
    emitter = getMultiAdapter((target, event), ILongPollEmitter)
    request = get_current_browser_request()
    ILongPollSubscriber(request).subscribe(emitter)
    return emitter.emit_key


def emit(source, event, data):
    emitter = getMultiAdapter((source, event), ILongPollEmitter)
    messaging.send(emitter.emit_key, data)


class JobLongPollEmitter:

    adapts(IJob, Interface)
    implements(ILongPollEmitter)

    def __init__(self, job, status):
        self.job = job
        if status not in JobStatus:
            raise AssertionError(
                "%r does not emit %r events." % (job, status))
        self.status = status

    @property
    def emit_key(self):
        return "longpoll.job.%d.%s" % (
            self.job.id, self.status.name)
