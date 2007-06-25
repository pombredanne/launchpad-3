# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Mailing list interfaces."""

__metaclass__ = type
__all__ = [
    'IMailingList',
    ]


from zope.interface import Attribute, Interface
from zope.schema import Datetime, Int, Text

from canonical.launchpad import _


class IMailingList:
    """A mailing list."""

    team = Attribute(_("The mailing list's team."))

    registrant = Attribute(_('The person who registered the mailing list.'))

    date_registered = Datetime(
        title=_('The date on which this mailing list was registered'),
        required=True, readonly=True)

    reviewer = Int(
        title=_('The person who reviewed this mailing list registration'),
        description=_('All mailing list registrations must be reviewed by '
                      'a Launchpad administrator.  The reviewer is the person '
                      'who formally accepts or declines the team mailing list '
                      'registration.  This may be None to indicate that the '
                      'list registration has not yet been reviewed.')
        )

    date_reviewed = Datetime(
        title=_('The date on which this mailing list registration was '
                'reviewed'),
        description=_('The date on which this mailing list registration was '
                      'reviewed by reviewer.  This may be None to indicate '
                      'that the list registration has not yet been reviewed.')
        )

    date_activated = Datetime(
        title_('The date on which this mailing list registration was '
               'activated'),
        description=("A team's mailing list is activated once (and if) the "
                     'Mailman process has successfully created it.  This '
                     'may be None to indicate that the list has not yet been '
                     'activated, or that its activation has failed.')
        )

    status = Int(
        title=_('The status of the mailing list'),
        required=True,
        )

    welcome_message_text = Text(
        title=_('The welcome message text for new subscribers'),

        description=_('When a new member joins the mailing list, they are '
                      'sent this welcome message text.  It may contain '
                      'any instructions or additional links that a new '
                      'subscriber might want to know about.')
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

    def reportConstructionResult(status):
        """Set the status after construction has occurred.

        This sets the status of the mailing list to reflect the results of
        construction by Mailman.  status may be either
        MailingListStatus.ACTIVE or MailingListStatus.FAILED.  When
        MailingListStatus.ACTIVE is given, this also sets the date_activated.
        Prior to the results being reported, the status of the mailing list
        must be MailingListStatus.CONSTRUCTING.
        """

    def deactivate():
        """Deactivate the mailing list.

        This sets the status to MailingListStatus.INACTIVE.  Prior to
        deactivation, the status of the mailing list must be
        MailingListStatus.ACTIVE.
        """


class IMailingListRegistry:
    """A mailing list registration service."""

    def register(team):
        """Register a team mailing list.

        A mailing list for the team is registered and the resulting
        `IMailingList` is returned.  The registrant will be the team's current
        owner and the registration time will be set to the current time.  The
        team must not yet have a mailing list.
        """

    def getTeamMailingList(team):
        """Return the IMailingList associated with the given team.

        None is returned if the team has no mailing list.
        """

    registered_lists = Attribute(
        'All mailing lists with a status of MailingListStatus.REGISTERED.')

    approved_lists = Attribute(
        'All mailing lists with the status of MailingListStatus.APPROVED.')
