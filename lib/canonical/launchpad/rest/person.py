# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonEntry',
    'PersonCollection',
    ]


from zope.component import adapts, getUtility

from canonical.lazr.rest import Collection, Entry
from canonical.launchpad.interfaces import (
    IPerson, IPersonEntry, IPersonSet, ITeam)
from canonical.lp import decorates


class PersonEntry(Entry):
    """A person or team."""
    adapts(IPerson)
    decorates(IPersonEntry)
    schema = IPersonEntry

    parent_collection_name = 'people'

    def fragment(self):
        """See `IEntry`."""
        return self.context.name

    def lookupCollection(self, name):
        """See `IEntry`."""
        if name == 'members' and self.context.isTeam():
            return getUtility(IPersonSet)


class PersonCollection(Collection):
    """A collection of people."""

    def lookupEntry(self, name):
        """Find a person by name."""
        person = self.context.getByName(name)
        if person is None:
            return None
        else:
            return person

    def find(self, scope, relationship):
        """Return all the people and teams on the site."""
        # Pass an empty query into find() to get all people
        # and teams.
        if scope is None:
            return self.context.find("")
        elif scope.context.isTeam() and relationship == 'members':
            return scope.context.allmembers
