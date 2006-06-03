# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Provides object snapshotting functionality. This is particularly
useful in calculating deltas"""

from sqlobject.main import SelectResults

from zope.schema import Field
from zope.interface.interfaces import IInterface
from zope.security.proxy import isinstance as zope_isinstance
from zope.interface import directlyProvides

from canonical.launchpad.fields import SnapshotAttribute


_marker = object()
# This list explicitly excludes Attribute, which is used to mark
# properties we calculate. Field is the base class used in most standard
# fields such as Int and Choice, and SnapshotAttribute allows specifying
# an attribute which /needs/ to be snapshotted.
snapshottables = (Field, SnapshotAttribute)


class SnapshotCreationError(Exception):
    """Something went wrong while creating a snapshot."""


class Snapshot:
    """Provides a simple snapshot of the given object.

    The snapshot will have the attributes given in attributenames. It
    will also provide the same interfaces as the original object.
    """
    def __init__(self, ob, names=None, providing=None):
        if names is None and providing is None:
            raise SnapshotCreationError(
                "You have to specify either 'names' or 'providing'.")

        if IInterface.providedBy(providing):
            providing = [providing]

        if names is None:
            names = set()
            for iface in providing:
                for name in iface.names(all=True):
                    field = iface[name]
                    if zope_isinstance(field, snapshottables):
                        # We only copy fields and attributes that have been
                        # specifically marked for snapshotting.
                        names.add(name)

        for name in names:
            value = getattr(ob, name, _marker)
            if zope_isinstance(value, SelectResults):
                # SQLMultipleJoin and SQLRelatedJoin return
                # SelectResults, which doesn't really help the
                # Snapshot object. We therefore list()ify the
                # values; this isn't perfect but allows deltas do be
                # generated reliably.
                value = list(value)
            setattr(self, name, value)

        if providing is not None:
            directlyProvides(self, providing)

