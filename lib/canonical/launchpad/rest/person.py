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
from canonical.lazr.interface import use_template
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.interfaces import (IPerson, IPersonSet,
                                            ITeamMembership)

from canonical.lazr import decorates


class IPersonEntry(IEntry):
    """The part of a person that we expose through the web service."""
    use_template(IPerson, include=["name", "displayname", "datecreated"])

    teamowner = Object(schema=IPerson, title=u"Team owner")

    members = CollectionField(value_type=Object(schema=IPerson))
    team_memberships = CollectionField(
        value_type=Object(schema=ITeamMembership))
    member_memberships = CollectionField(
        value_type=Object(schema=ITeamMembership))

class PersonEntry(Entry):
    """A person or team."""
    adapts(IPerson)
    decorates(IPersonEntry)
    schema = IPersonEntry

    _parent_collection_path = ['people']

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
