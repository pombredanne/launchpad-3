# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll adapters."""

__metaclass__ = type
__all__ = []


from uuid import uuid4

from .interfaces import ILongPollSubscriber
from zope.interface import implements


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
