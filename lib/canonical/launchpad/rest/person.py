# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonEntry',
    'PersonCollection',
    ]


from zope.component import adapts

from canonical.lazr.rest import Collection, Entry
from canonical.launchpad.interfaces import IPerson, IPersonEntry, ITeam
from canonical.lp import decorates


class PersonEntry(Entry):
    """A person or team."""
    adapts(IPerson)
    decorates(IPersonEntry)
    schema = IPersonEntry

    parent_collection_name = 'people'

    def lookupEntry(self, name):
        """See `IEntry`."""
        if name == 'owner' and self.context.isTeam():
            return self.context.teamowner

    def fragment(self):
        """See `IEntry`."""
        return self.context.name


class PersonCollection(Collection):
    """A collection of people."""

    def lookupEntry(self, name):
        """Find a person by name."""
        person = self.context.getByName(name)
        if person is None:
            return None
        else:
            return person

    def find(self):
        """Return all the people on the site."""
        return self.context.find("")
