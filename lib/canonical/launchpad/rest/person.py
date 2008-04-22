# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'GetMembersByStatusOperation',
    'GetPeopleOperation',
    'IPersonEntry',
    'PersonEntry',
    'PersonFactoryOperation'
    ]

from zope.component import adapts, getUtility
from zope.interface import classProvides
from zope.schema import Choice, Object, TextLine

from canonical.lazr.rest import Entry
from canonical.lazr.interface import use_template
from canonical.lazr.interfaces import IEntry, IEntryWADLSpecification
from canonical.lazr.rest.schema import CollectionField
from canonical.lazr.rest import ResourceGETOperation, ResourcePOSTOperation

from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.interfaces import (
    EmailAddressAlreadyTaken, IPerson, ILaunchBag, ITeamMembership,
    PersonCreationRationale, TeamMembershipStatus)
from canonical.launchpad.webapp import canonical_url

from canonical.lazr import decorates


class IPersonEntry(IEntry):
    """The part of a person that we expose through the web service."""
    use_template(IPerson, include=["name", "displayname", "datecreated"])

    teamowner = PublicPersonChoice(
        title=u'Team owner', required=False, readonly=False,
        vocabulary='ValidTeamOwner')

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
    classProvides(IEntryWADLSpecification)

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

    XXX leonardr 2008-04-01 bug=210265:
    To implement this without creating a custom operation, expose a
    'status' filter on a collection of team memberships or team
    members.
    """

    params = (Choice(__name__='status', vocabulary=TeamMembershipStatus),)

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

    XXX leonardr 2008-04-01 bug=210265:
    To implement this without creating a custom operation, expose a
    'status' filter on the collection of people.
    """

    params = (TextLine(__name__='text'),)

    def call(self, text):
        """Execute the operation.

        :param text: A search filter.
        """
        return self.context.find(text)


class PersonFactoryOperation(ResourcePOSTOperation):
    """An operation that creates a new person.

    XXX leonardr 2008-04-01 bug=210265:
    To implement this without creating a custom operation, define a
    standard factory method for PersonCollection.
    """

    params = (
        TextLine(__name__='email_address', required=True),
        TextLine(__name__='comment', required=False),
        TextLine(__name__='name', required=False),
        TextLine(__name__='display_name', required=False),
        TextLine(__name__='password', required=False),
        )

    def call(self, email_address, comment, name,
             display_name, password):
        """Execute the operation.

        :param email_address: An email address for the new person.
        :param comment: Comment on the person's creation. Must be of
           the following form: "when %(action_details)s" (e.g. "when
           the foo package was imported into Ubuntu Breezy").
        :param name: The person's Launchpad name.
        :param display_name: The person's display name.
        :param password: The person's password.

        :return: The empty string.
        """
        user = getUtility(ILaunchBag).user
        try:
            person, emailaddress = self.context.createPersonAndEmail(
                email_address,
                PersonCreationRationale.OWNER_CREATED_LAUNCHPAD,
                comment, name, display_name, password, registrant=user)
        except EmailAddressAlreadyTaken:
            self.request.response.setStatus(409) # Conflict
            return "The email address '%s' is already in use." % email_address
        if person is None:
            # XXX leonardr 2008-04-01 bug=210389
            # Unfortunately we don't know why person creation failed,
            # only that it did fail.
            self.request.response.setStatus(400)
        else:
            self.request.response.setStatus(201)
            self.request.response.setHeader("Location",
                                            canonical_url(person))
        return ''
