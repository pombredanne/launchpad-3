# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Mailing list interfaces."""

__metaclass__ = type
__all__ = [
    'IMailingList',
    'IMailingListRegistry',
    ]


from zope.interface import Attribute, Interface
from zope.schema import Datetime, Int, Text

from canonical.launchpad import _


class IMailingList(Interface):
    """A mailing list."""

    team = Attribute(_("The mailing list's team."))

    registrant = Attribute(_('The person who registered the mailing list.'))

    date_registered = Datetime(
        title=_('Registration date'),
        description=_('The date on which this mailing list was registered.'),
        required=True, readonly=True)

    reviewer = Attribute(
        _('The person who reviewed this mailing list registration'))

    date_reviewed = Datetime(
        title=_('Review date'),
        description=_('The date on which this mailing list registration was '
                      'reviewed.  This may be None to indicate that the list '
                      'registration has not yet been reviewed.')
        )

    date_activated = Datetime(
        title=_('Activation date'),
        description=_('The date on which this mailing list was activated, '
                      'meaning that the Mailman process has successfully '
                      'created it.  This may be None to indicate that the '
                      'mailing list has not yet been activated, or that its '
                      'activation has failed.')
        )

    status = Int(
        title=_('The status of the mailing list'),
        description=_('The status of the mailing list.'),
        required=True,
        )

    welcome_message = Text(
        title=_('The welcome message text for new subscribers'),
        description=_('When a new member joins the mailing list, they are '
                      'sent this welcome message text.  It may contain '
                      'any instructions or additional links that a new '
                      'subscriber might want to know about.  The welcome '
                      'message may only be changed for active mailing lists '
                      'and doing so changes the status of the list to '
                      'MODIFIED.')
        )

    def review(reviewer, status):
        """Review the mailing list's registration.

        The reviewer is the person reviewing the mailing list.  status may be
        only MailingListStatus.APPROVED or MailingListStatus.DECLINED.  Prior
        to the review, the status of the mailing list must be
        MailingListStatus.REGISTERED.
        """

    def construct():
        """Set the status to the MailingListStatus.CONSTRUCTING state.

        This state change happens when Mailman pulls the list approved mailing
        lists and begins constructing them.  Prior to constructing, the status
        of the mailing list must be MailingListStatus.APPROVED.
        """

    def reportResult(status):
        """Set the status after a remote action has taken place.

        This sets the status of the mailing list to reflect the results of
        action by Mailman.  It handles various state changes, updating other
        attributes such as the activate date as necessary.
        """

    def deactivate():
        """Deactivate the mailing list.

        This sets the status to MailingListStatus.INACTIVE.  Prior to
        deactivation, the status of the mailing list must be
        MailingListStatus.ACTIVE.
        """


class IMailingListRegistry(Interface):
    """A mailing list registration service."""

    def register(team):
        """Register a team mailing list.

        A mailing list for the team is registered and the resulting
        `IMailingList` is returned.  The registrant will be the team's current
        owner and the registration time will be set to the current time.  The
        team must not yet have a mailing list.
        """

    def getTeamMailingList(team_name):
        """Return the IMailingList associated with the given team name.

        None is returned if the named team has no mailing list.
        """

    registered_lists = Attribute(
        'All mailing lists with a status of MailingListStatus.REGISTERED.')

    approved_lists = Attribute(
        'All mailing lists with the status of MailingListStatus.APPROVED.')

    modified_lists = Attribute(
        'All mailing lists with the status of MailingListStatus.MODIFIED.')

    deactivated_lists = Attribute(
        'All mailing lists with the status of MailingListStatus.DEACTIVATING.')
