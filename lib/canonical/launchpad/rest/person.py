# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonEntry',
    'PersonCollection',
    ]


from zope.component import adapts, getUtility
from zope.interface import implements
from canonical.lazr.interfaces import ICollection
from canonical.lazr.rest import EntryResource
from canonical.launchpad.interfaces import IPerson, IPersonEntry, IPersonSet
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

    def lookupEntry(self, name):
        """Find a person by name."""
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return None
        else:
            return EntryResource(person, self.request)

    def find(self):
        return [EntryResource(p, self.request) for p in
                getUtility(IPersonSet).getAllValidPersons()]
