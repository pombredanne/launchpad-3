# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Team membership interfaces."""

__metaclass__ = type

__all__ = ['ITeamMembership', 'ITeamMembershipSet', 'ITeamMember',
           'ITeamParticipation', 'DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT']

from zope.schema import Choice, Int, Text
from zope.interface import Interface, Attribute

from canonical.launchpad import _

# One week before a membership expires we send a notification to the member,
# either inviting him to renew his own membership or asking him to get a team
# admin to do so, depending on the team's renewal policy.
DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT = 7


class ITeamMembership(Interface):
    """TeamMembership for Users"""

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Member"), required=True, readonly=False)
    reviewer = Int(title=_("Reviewer"), required=False, readonly=False)

    datejoined = Text(
        title=_("Date Joined"), required=True, readonly=True,
        description=_(
            "If this is an active membership, it contains the date in which "
            "the membership was approved. If this is a proposed membership, "
            "it contains the date the user asked to join."))
    dateexpires = Text(title=_("Date Expires"), required=False, readonly=False)
    reviewercomment = Text(title=_("Reviewer Comment"), required=False,
                           readonly=False)
    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=True)

    statusname = Attribute("Status Name")

    def isExpired():
        """Return True if this membership's status is EXPIRED."""

    def canChangeExpirationDate(person):
        """Can the given person change this membership's expiration date?

        A membership's expiration date can be changed by the team owner, by a
        Launchpad admin or by a team admin. In the latter case, though, the
        expiration date can only be changed if the admin is not changing his
        own membership.
        """

    def setExpirationDate(date, user):
        """Set this membership's expiration date.

        The given date must be None or in the future and the given user must
        be allowed to change this membership's expiration date as per the
        rules defined in canChangeExpirationDate().
        """

    def canBeRenewedByMember():
        """Can this membership be renewed by the member himself?

        A membership can be renewed if the team's renewal policy is ONDEMAND,
        the membership itself is active (status = [ADMIN|APPROVED]) and it's
        set to expire in less than DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT days.
        """

    def sendSelfRenewalNotification():
        """Send an email to the team admins notifying that this membership
        has been renewed by the member himself.

        This method must not be called if the team's renewal policy is not
        ONDEMAND.
        """

    def sendAutoRenewalNotification():
        """Send an email to the member and to team admins notifying that this
        membership has been automatically renewed.

        This method must not be called if the team's renewal policy is not
        AUTOMATIC.
        """

    def sendExpirationWarningEmail():
        """Send an email to the member warning him that this membership will
        expire soon.
        """

    def setStatus(status, reviewer, reviewercomment=None):
        """Set the status of this membership.

        Also sets the reviewer and reviewercomment, filling or cleaning
        the TeamParticipation table if necessary.

        The given status must be different than the current status.
        """


class ITeamMembershipSet(Interface):
    """A Set for TeamMembership objects."""

    def handleMembershipsExpiringToday(reviewer):
        """Expire or renew the memberships flagged to expire today.

        If the team's renewal policy is AUTOMATIC, renew the membership
        (keeping the same status) and send a notification to the member and
        team admins. Otherwise flag the membership as expired.
        """

    def getMembershipsToExpire(when=None):
        """Return all TeamMemberships that should be expired.

        If when is None, we use datetime.now().

        A TeamMembership should be expired when its expiry date is prior or
        equal to :when: and its status is either ADMIN or APPROVED.
        """

    def new(person, team, status, dateexpires=None, reviewer=None,
            reviewercomment=None):
        """Create and return a new TeamMembership object.

        The status of this new object must be APPROVED, PROPOSED or ADMIN. If
        the status is APPROVED or ADMIN, this method will also take care of
        filling the TeamParticipation table.
        """

    def getByPersonAndTeam(person, team):
        """Return the TeamMembership object for the given person and team.

        If the given person or team is None, there will obviously be no
        TeamMembership and I'll return None.
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

