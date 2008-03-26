# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'GetMembersByStatusOperation',
    'GetPeopleOperation',
    'IPersonEntry',
    'PersonCollection',
    'PersonEntry',
    ]

from zope.component import adapts
from zope.schema import Choice, Object, TextLine

from canonical.lazr.rest import Collection, Entry
from canonical.lazr.interface import use_template
from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest.schema import CollectionField
from canonical.lazr.rest import ResourceGETOperation

from canonical.launchpad.interfaces import (
    IPerson, ITeamMembership, TeamMembershipStatus)

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


class GetMembersByStatusOperation(ResourceGETOperation):
    """An operation that retrieves team members with the given status.

    Note for future: to implement this without creating a custom
    operation, expose a 'status' filter on a collection of team
    memberships or team members.
    """

    params = [ Choice(__name__='status', vocabulary=TeamMembershipStatus) ]

    def call(self, status):
        """Execute the operation.

        :param status: A DBItem from TeamMembershipStatus.

        :return: A list of people whose membership in this team is of
        the given status.
        """
        return self.context.getMembersByStatus(status.value)


class GetPeopleOperation(ResourceGETOperation):
    """An operation that retrieves people that match the given filter.

    XXX leonardr 2008-03-17: This operation does not support
    IPersonSet.find()'s method's 'orderBy' argument because that
    method directly exposes the Launchpad database schema. If we
    want to expose it, we must write code that maps some subset of
    the web service schema to the database schema.

    Note for future: to implement this without creating a custom
    operation, expose a 'status' filter on the collection of people.
    """

    params = [ TextLine(__name__='text') ]

    def call(self, text):
        """Execute the operation.

        :param text: A search filter.
        """
        return self.context.find(text)


class PersonCollection(Collection):
    """A collection of people."""

    def find(self):
        """Return all the people and teams on the site."""
        # Pass an empty query into find() to get all people
        # and teams.
        return self.context.find("")

