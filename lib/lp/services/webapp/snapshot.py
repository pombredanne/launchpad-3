# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snapshot helpers."""

from contextlib import contextmanager

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.interfaces import ISnapshotValueFactory
from lazr.lifecycle.snapshot import Snapshot
from storm.zope.interfaces import IResultSet
from zope.component import adapter
from zope.event import notify
from zope.interface import (
    implementer,
    providedBy,
    )

from lp.services.helpers import shortlist


HARD_LIMIT_FOR_SNAPSHOT = 1000


@implementer(ISnapshotValueFactory)
@adapter(IResultSet)  # And ISQLObjectResultSet.
def snapshot_sql_result(value):
    """Snapshot adapter for the Storm result set."""
    # SQLMultipleJoin and SQLRelatedJoin return
    # SelectResults, which doesn't really help the Snapshot
    # object. We therefore list()ify the values; this isn't
    # perfect but allows deltas to be generated reliably.
    return shortlist(
        value, longest_expected=100, hardlimit=HARD_LIMIT_FOR_SNAPSHOT)


@contextmanager
def notify_modified(obj, edited_fields, snapshot_names=None, user=None):
    """A context manager that notifies about modifications to an object.

    Use this as follows::

        with notify_modified(obj, ["attr"]):
            obj.attr = value

    Or::

        edited_fields = set()
        with notify_modified(obj, edited_fields):
            if obj.attr != new_attr:
                obj.attr = new_attr
                edited_fields.add("attr")

    Or even::

        edited_fields = set()
        with notify_modified(obj, edited_fields) as previous_obj:
            do_something()
            if obj.attr != previous_obj.attr:
                edited_fields.add("attr")

    :param obj: The object being modified.
    :param edited_fields: An iterable of fields being modified.  This is not
        used until after the block wrapped by the context manager has
        finished executing, so you can safely pass a mutable object and add
        items to it from inside the block as you determine which fields are
        being modified.  A notification will only be sent if `edited_fields`
        is non-empty.
    :param snapshot_names: If not None, only snapshot these names.  This may
        be used if snapshotting some of the object's attributes is expensive
        in some contexts (and they can't be wrapped by `doNotSnapshot` for
        some reason).
    :param user: If not None, the user making these changes.  If None,
        defaults to the principal registered in the current interaction.
    """
    obj_before_modification = Snapshot(
        obj, names=snapshot_names, providing=providedBy(obj))
    yield obj_before_modification
    edited_fields = list(edited_fields)
    if edited_fields:
        notify(ObjectModifiedEvent(
            obj, obj_before_modification, edited_fields, user=user))
