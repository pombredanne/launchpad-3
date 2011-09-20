# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll lifecycle adapters."""

__metaclass__ = type
__all__ = []

from lazr.lifecycle.interfaces import (
    IObjectCreatedEvent,
    IObjectDeletedEvent,
    IObjectModifiedEvent,
    )
from storm.base import Storm
from storm.info import get_obj_info
from zope.component import adapter
from zope.interface import implements

from lp.services.longpoll.adapters.event import (
    generate_event_key,
    LongPollEvent,
    )
from lp.services.longpoll.interfaces import ILongPollEvent


class LongPollStormLifecycleEvent(LongPollEvent):

    implements(ILongPollEvent)

    @property
    def event_key(self):
        cls_info = get_obj_info(self.source).cls_info
        key_parts = [cls_info.table.name.lower()]
        key_parts.extend(
            primary_key_column.__get__(self.source)
            for primary_key_column in cls_info.primary_key)
        key_parts.append(self.event)
        return generate_event_key(*key_parts)


@adapter(Storm, IObjectCreatedEvent)
def storm_object_created(model_instance, object_event):
    event = LongPollStormLifecycleEvent(model_instance, "created")
    event.emit({})


@adapter(Storm, IObjectDeletedEvent)
def storm_object_deleted(model_instance, object_event):
    event = LongPollStormLifecycleEvent(model_instance, "deleted")
    event.emit({})


@adapter(Storm, IObjectModifiedEvent)
def storm_object_modified(model_instance, object_event):
    event = LongPollStormLifecycleEvent(model_instance, "modified")
    event.emit({"edited_fields": sorted(object_event.edited_fields)})
