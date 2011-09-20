# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll life-cycle adapters."""

from __future__ import absolute_import

__metaclass__ = type
__all__ = []

from lazr.lifecycle.interfaces import (
    IObjectCreatedEvent,
    IObjectDeletedEvent,
    IObjectModifiedEvent,
    )
from storm.base import Storm
from storm.info import get_obj_info
from zope.component import (
    adapter,
    adapts,
    )
from zope.interface import implements

from lp.services.longpoll.adapters.event import (
    generate_event_key,
    LongPollEvent,
    )
from lp.services.longpoll.interfaces import ILongPollEvent


class LongPollStormEvent(LongPollEvent):
    """A `ILongPollEvent` for events of `Storm` objects.

    This class knows how to construct a stable event key given a Storm object.
    """

    adapts(Storm)
    implements(ILongPollEvent)

    @property
    def event_key(self):
        """See `ILongPollEvent`.

        Constructs the key from the table name and primary key values of the
        Storm model object.
        """
        cls_info = get_obj_info(self.source).cls_info
        return generate_event_key(
            cls_info.table.name.lower(), *(
                primary_key_column.__get__(self.source)
                for primary_key_column in cls_info.primary_key))


@adapter(Storm, IObjectCreatedEvent)
def object_created(model_instance, object_event):
    """Subscription handler for `Storm` creation events."""
    event = LongPollStormEvent(model_instance)
    event.emit({"event_name": "created"})


@adapter(Storm, IObjectDeletedEvent)
def object_deleted(model_instance, object_event):
    """Subscription handler for `Storm` deletion events."""
    event = LongPollStormEvent(model_instance)
    event.emit({"event_name": "deleted"})


@adapter(Storm, IObjectModifiedEvent)
def object_modified(model_instance, object_event):
    """Subscription handler for `Storm` modification events."""
    edited_fields = sorted(object_event.edited_fields)
    event = LongPollStormEvent(model_instance)
    event.emit(
        {"event_name": "modified",
         "edited_fields": edited_fields})
