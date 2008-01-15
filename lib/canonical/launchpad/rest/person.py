# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonEntry',
    'PersonCollection',
    ]


from zope.component import adapts
from zope.interface import implements
from canonical.lazr.interfaces import ICollection
from canonical.lazr.rest import EntryResource
from canonical.launchpad.interfaces import IPerson, IPersonEntry
from canonical.lp import decorates


class PersonEntry:
    """A person."""
    adapts(IPerson)
    decorates(IPersonEntry)
    schema = IPersonEntry

    def __init__(self, context):
        self.context = context


class PersonCollection:
    """A collection of people."""
    implements(ICollection)

    def __init__(self, context):
        self.context = context

    def find(self):
        return self.context.getAllValidPersons()
