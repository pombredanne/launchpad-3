# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'IPersonEntry',
    'PersonCollection',
    'PersonEntry',
    'PersonPersonCollection',
    ]

from zope.component import adapts, getUtility
from zope.schema import Object

from canonical.lazr.rest import Collection, Entry, ScopedCollection
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.interfaces import (
    IPerson, IPersonSet, ITeamMembership, make_person_name_field)

from canonical.lp import decorates

class IPersonEntry(IEntry):
    """The part of a person that we expose through the web service."""

    # XXX leonardr 2008-01-28 bug=186702 A much better solution would
    # let us reuse or copy fields from IPerson.
    name = make_person_name_field()
    teamowner = Object(schema=IPerson)
    members = CollectionField(value_type=Object(schema=IPerson))
    team_memberships = CollectionField(
        relationship_name = 'teams',
        value_type=Object(schema=ITeamMembership), is_entry_container=True)
    member_memberships = CollectionField(
        relationship_name = 'members',
        value_type=Object(schema=ITeamMembership), is_entry_container=True)

class PersonEntry(Entry):
    """A person or team."""
    adapts(IPerson)
    decorates(IPersonEntry)
    schema = IPersonEntry

    parent_collection_name = 'people'

    @property
    def members(self):
        """See `IPersonEntry`."""
        if not self.context.isTeam():
            return None
        return self.context.activemembers

    @property
    def team_memberships(self):
        """See `IPersonEntry`."""
        return self.context.myactivememberships

    @property
    def member_memberships(self):
        """See `IPersonEntry`."""
        if not self.context.isTeam():
            return None
        return self.context.getActiveMemberships()


class PersonCollection(Collection):
    """A collection of people."""

    def getEntryPath(self, entry):
        """See `ICollection`."""
        return entry.name

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
        # and teams.
        return self.context.find("")


class PersonPersonCollection(ScopedCollection):
    """A collection of people associated with some other person.

    For instance, the members of a team are a collection of people
    associated with another person.
    """

    def lookupEntry(self, name):
        """Find a person in the collection by name."""
        person = getUtility(IPersonSet).getByName(name)
        if person in self.collection:
            return person
        return None
