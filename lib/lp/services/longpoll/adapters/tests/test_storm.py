# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll event adapter tests."""

__metaclass__ = type

from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectDeletedEvent,
    ObjectModifiedEvent,
    )
from storm.base import Storm
from storm.properties import Int
from zope.event import notify

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.longpoll.testing import (
    capture_longpoll_emissions,
    LongPollEventRecord,
    )
from lp.testing import TestCase


class FakeStormClass(Storm):

    __storm_table__ = 'FakeTable'

    id = Int(primary=True)


class TestStormLifecycle(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_storm_object_created(self):
        storm_object = FakeStormClass()
        storm_object.id = 1234
        with capture_longpoll_emissions() as log:
            notify(ObjectCreatedEvent(storm_object))
        expected = [
            LongPollEventRecord(
                "longpoll.event.faketable.1234.created",
                {"event_key": "longpoll.event.faketable.1234.created",
                 "event_data": {}}),
            ]
        self.assertEqual(expected, log)

    def test_storm_object_deleted(self):
        storm_object = FakeStormClass()
        storm_object.id = 1234
        with capture_longpoll_emissions() as log:
            notify(ObjectDeletedEvent(storm_object))
        expected = [
            LongPollEventRecord(
                "longpoll.event.faketable.1234.deleted",
                {"event_key": "longpoll.event.faketable.1234.deleted",
                 "event_data": {}}),
            ]
        self.assertEqual(expected, log)

    def test_storm_object_modified(self):
        storm_object = FakeStormClass()
        storm_object.id = 1234
        with capture_longpoll_emissions() as log:
            notify(ObjectModifiedEvent(
                    storm_object, storm_object, ("itchy", "scratchy")))
        expected = [
            LongPollEventRecord(
                "longpoll.event.faketable.1234.modified",
                {"event_key": "longpoll.event.faketable.1234.modified",
                 "event_data": {"edited_fields": ["itchy", "scratchy"]}}),
            ]
        self.assertEqual(expected, log)

    def test_storm_object_no_edited_fields(self):
        # A longpoll event is not emitted unless edited_fields is populated.
        storm_object = FakeStormClass()
        storm_object.id = 1234
        with capture_longpoll_emissions() as log:
            notify(ObjectModifiedEvent(storm_object, storm_object, None))
        self.assertEqual([], log)
        with capture_longpoll_emissions() as log:
            notify(ObjectModifiedEvent(storm_object, storm_object, ()))
        self.assertEqual([], log)
