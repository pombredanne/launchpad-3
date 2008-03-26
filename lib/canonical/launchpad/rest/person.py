# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'IPersonEntry',
    'PersonCollection',
    'PersonEntry',
    ]

from zope.component import adapts
from zope.schema import Object

from canonical.lazr.rest import Collection, Entry
from canonical.lazr.interface import use_template
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.interfaces import IPerson, ITeamMembership

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

    def find(self):
        """Return all the people and teams on the site."""
        # Pass an empty query into find() to get all people
        # and teams.
        return self.context.find("")

