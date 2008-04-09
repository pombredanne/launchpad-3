# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Provides object snapshotting functionality. This is particularly
useful in calculating deltas"""

from sqlos.interfaces import ISelectResults

from zope.interface.interfaces import IInterface
from zope.interface import directlyProvides
from zope.schema.interfaces import IField


_marker = object()


class SnapshotCreationError(Exception):
    """Something went wrong while creating a snapshot."""


class Snapshot:
    """Provides a simple snapshot of the given object.

    The snapshot will have the attributes listed in names. It
    will also provide the interfaces listed in providing. If no names
    are supplied but an interface is provided, all Fields of that
    interface will be included in the snapshot.
    """
    def __init__(self, ob, names=None, providing=None):
        from canonical.launchpad.helpers import shortlist

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
                    if IField.providedBy(field):
                        # Only Fields are actually copied over to the
                        # snapshot.
                        # XXX kiko 2006-06-05 bug=48575: this is actually
                        # rather counterintuitive, and I believe the proper
                        # solution is to just make names mandatory.
                        names.add(name)

        for name in names:
            value = getattr(ob, name, _marker)
            if value is _marker:
                raise AssertionError("Attribute %s not in object %r"
                                     % (name, ob))
            if ISelectResults.providedBy(value):
                # SQLMultipleJoin and SQLRelatedJoin return
                # SelectResults, which doesn't really help the Snapshot
                # object. We therefore list()ify the values; this isn't
                # perfect but allows deltas do be generated reliably.
                value = shortlist(value, longest_expected=100)
            setattr(self, name, value)

        if providing is not None:
            directlyProvides(self, providing)

    def __eq__(self, other):
        return bool(self.__dict__ == other.__dict__)
