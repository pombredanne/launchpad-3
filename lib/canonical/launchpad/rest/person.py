# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonEntry',
    'PersonCollection',
    'PersonPersonCollection'
    ]


from zope.component import adapts, getUtility

from canonical.lazr.rest import Collection, Entry, ScopedCollection
from canonical.launchpad.interfaces import (
    IPerson, IPersonEntry, IPersonSet)
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

    @property
    def members(self):
        """See `IPersonEntry`."""
        if not self.context.isTeam():
            return None
        return self.context.activemembers


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
        """Return all the people and teams on the site."""
        # Pass an empty query into find() to get all people
        # =and teams.
        return self.context.find("")


class PersonPersonCollection(ScopedCollection):
    """A collection of people associated with some other person.

    For instance, the members of a team.
    """

    def lookupEntry(self, name):
        person = getUtility(IPersonSet).getByName(name)
        if person in self.collection:
            return person
        return None