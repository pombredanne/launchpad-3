# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = []


from uuid import uuid4

from .interfaces import ILongPollSubscriber
from zope.component import adapter
from zope.interface import (
    implementer,
    implements,
    )
from zope.publisher.interfaces import IApplicationRequest


class LongPollSubscriber:

    implements(ILongPollSubscriber)

    def __init__(self, request):
        self.request = request
        self.subscribe_uuid = uuid4()

    @property
    def subscribe_key(self):
        return str(self.subscribe_uuid)

    def subscribe(self, emitter):
        pass


LongPollSubscriber.ANNOTATION_KEY = "%s.%s" % (
    LongPollSubscriber.__module__, LongPollSubscriber.__name__)


@adapter(IApplicationRequest)
@implementer(ILongPollSubscriber)
def long_poll_subscriber(request):
    annotations = request.annotations
    subscriber = annotations.get(LongPollSubscriber.ANNOTATION_KEY)
    if subscriber is None:
        subscriber = LongPollSubscriber(request)
        annotations[LongPollSubscriber.ANNOTATION_KEY] = subscriber
    return subscriber
