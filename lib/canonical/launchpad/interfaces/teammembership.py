# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Team membership interfaces."""

__metaclass__ = type

__all__ = ['ITeamMembership', 'ITeamMembershipSet', 'ITeamMember',
           'ITeamParticipation']

from zope.schema import Choice, Int, Text
from zope.interface import Interface, Attribute

from canonical.launchpad import _


class ITeamMembership(Interface):
    """TeamMembership for Users"""

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Member"), required=True, readonly=False)
    reviewer = Int(title=_("Reviewer"), required=False, readonly=False)

    datejoined = Text(title=_("Date Joined"), required=True, readonly=True)
    dateexpires = Text(title=_("Date Expires"), required=False, readonly=False)
    reviewercomment = Text(title=_("Reviewer Comment"), required=False,
                           readonly=False)
    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=False)

    # Properties
    statusname = Attribute("Status Name")
    is_admin = Attribute("True if the person is an admin of the team.")
    is_owner = Attribute("True if the person is the team owner.")

    def isExpired():
        """Return True if this membership's status is EXPIRED."""


class ITeamMembershipSet(Interface):
    """A Set for TeamMembership objects."""

    def getActiveMemberships(team, orderBy=None):
        """Return all active TeamMemberships for the given team.

        Active memberships are the ones with status APPROVED or ADMIN.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getInactiveMemberships(team, orderBy=None):
        """Return all inactive TeamMemberships for the given team.

        Inactive memberships are the ones with status EXPIRED or DEACTIVATED.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getProposedMemberships(team, orderBy=None):
        """Return all proposed TeamMemberships for the given team.

        Proposed memberships are the ones with status PROPOSED.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getByPersonAndTeam(personID, team, default=None):
        """Return the TeamMembership object for the given person and team.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """

    def getTeamMembersCount(team):
        """Return the number of members this team have.

        This includes active, inactive and proposed members.
        """


class ITeamMember(Interface):
    """The interface used in the form to add a new member to a team."""

    newmember = Choice(title=_('New member'), required=True,
                       vocabulary='ValidTeamMember',
                       description=_("The user or team which is going to be "
                                     "added as the new member of this team."))


class ITeamParticipation(Interface):
    """A TeamParticipation.

    A TeamParticipation object represents a person being a member of a team.
    Please note that because a team is also a person in Launchpad, we can
    have a TeamParticipation object representing a team that is a member of
    another team. We can also have an object that represents a person being a
    member of itself.
    """

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("The team"), required=True, readonly=False)
    person = Int(title=_("The member"), required=True, readonly=False)

