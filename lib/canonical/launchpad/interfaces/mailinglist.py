# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Mailing list interfaces."""

__metaclass__ = type
__all__ = [
    'IMailingList',
    'IMailingListSet',
    'MailingListStatus',
    ]


from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Set, Text

from canonical.launchpad import _
from canonical.lazr.enum import DBEnumeratedType, DBItem


class MailingListStatus(DBEnumeratedType):
    """Team mailing list status.

    Team mailing lists can be in one of several states, which this class
    tracks.  A team owner first requests that a mailing list be created for
    their team; this is called registering the list.  This request will then
    be either approved or declined by a Launchpad administrator.

    If a list request is approved, its creation will be requested of Mailman,
    but it takes time for Mailman to act on this request.  During this time,
    the state of the list is 'constructing'.  Mailman will then either succeed
    or fail to create the list.  If it succeeds, the list is active until such
    time as the team owner requests that the list be made inactive.
    """

    REGISTERED = DBItem(1, """
        Registered; request creation

        The team owner has requested that the mailing list for their team be
        created.
        """)

    APPROVED = DBItem(2, """
        Approved

        A Launchpad administrator has approved the request to create the team
        mailing list.
        """)

    DECLINED = DBItem(3, """
        Declined

        A Launchpad administrator has declined the request to create the team
        mailing list.
        """)

    CONSTRUCTING = DBItem(4, """
        Constructing

        Mailman is in the process of constructing a mailing list that has been
        approved for creation.
        """)

    ACTIVE = DBItem(5, """
        Active

        Mailman has successfully created the mailing list, and it is now
        active.
        """)

    FAILED = DBItem(6, """
        Failed

        Mailman was unsuccessful in creating the mailing list.
        """)

    INACTIVE = DBItem(7, """
        Inactive

        A previously active mailing lit has been made inactive by its team
        owner.
        """)

    MODIFIED = DBItem(8, """
        Modified

        An active mailing list has been modified and this modification needs
        to be communicated to Mailman.
        """)

    DEACTIVATING = DBItem(9, """
        Deactivating

        The mailing list has been flagged for deactivation by the team owner.
        Mailman will be informed of this and will take the necessary actions
        to deactive the list.
        """)


class IMailingList(Interface):
    """A mailing list."""

    team = Choice(
        title=_('Team'),
        description=_('The team that this mailing list is associated with.'),
        vocabulary='ValidTeam',
        required=True, readonly=True)

    registrant = Choice(
        title=_('Registrant'),
        description=_('The person who registered the mailing list.'),
        vocabulary='ValidPersonOrTeam',
        required=True, readonly=True)

    date_registered = Datetime(
        title=_('Registration date'),
        description=_('The date on which this mailing list was registered.'),
        required=True, readonly=True)

    reviewer = Choice(
        title=_('Reviewer'),
        description=_(
            'The person who reviewed this mailing list registration, or '
            'None if the registration has not yet been reviewed.'),
        vocabulary='ValidPersonOrTeam')

    date_reviewed = Datetime(
        title=_('Review date'),
        description=_('The date on which this mailing list registration was '
                      'reviewed, or None if the registration has not yet '
                      'been reviewed.')
        )

    date_activated = Datetime(
        title=_('Activation date'),
        description=_('The date on which this mailing list was activated, '
                      'meaning that the Mailman process has successfully '
                      'created it.  This may be None if the mailing list '
                      'has not yet been activated, or that its activation '
                      'has failed.')
        )

    status = Choice(
        title=_('Status'),
        description=_('The status of the mailing list.'),
        vocabulary='MailingListStatus',
        required=True,
        )

    welcome_message = Text(
        title=_('Welcome message text'),
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

        :param reviewer: The person who reviewed the mailing list registration
            request.
        :param status: The status that the reviewer is giving this
            registration request.  `status` must be be either
            `MailingListStatus.APPROVED` or `MailingListStatus.DECLINED`.
            Prior to the review, the status of the mailing list must be
            `MailingListStatus.REGISTERED`.
        :raises AssertionError: When the mailing list is not in the
            `MailingListStatus.REGISTERED` state, or `status` is an invalid
            value.
        """

    def startConstructing():
        """Set the status to the `MailingListStatus.CONSTRUCTING` state.

        This state change happens when Mailman pulls the list approved mailing
        lists and begins constructing them.

        :raises AssertionError: When prior to constructing, the status of the
            mailing list is not `MailingListStatus.APPROVED`.
        """

    def transitionToStatus(target_state):
        """Transition the list's state after a remote action has taken place.

        This sets the status of the mailing list to reflect the results of
        action by Mailman.  It handles various state changes, updating other
        attributes such as the activate date as necessary.

        :param target_state: The new state.
        :raises AssertionError: When an invalid state transition is made.
        """

    def deactivate():
        """Deactivate the mailing list.

        This sets the status to `MailingListStatus.INACTIVE`.

        :raises AssertionError: When prior to deactivation, the status of the
            mailing list is not `MailingListStatus.ACTIVE`.
        """


class IMailingListSet(Interface):
    """A set of mailing lists."""

    def new(team, registrant=None):
        """Register a new team mailing list.

        A mailing list for the team is registered and the resulting
        `IMailingList` is returned.  The registration time will be set to the
        current time.  The team must not yet have a mailing list.

        :param team: The team to register a new mailing list for.
        :param registrant: The person registering the mailing list.  This must
            be the team owner or one of the team admins.  If None, the team
            owner is used.
        :raises AssertionError: When `team` is not a team, already has a
            mailing list registered for it, or the registrant is not a team
            owner or admin.
        """

    def get(team_name):
        """Return the `IMailingList` associated with the given team name.

        :param team_name: The name of the team to get the mailing list for.
        :return: The `IMailingList` for the named team or None if no mailing
            list is registered for the named team, or the team doesn't exist.
        :raises AssertionError: When `team_name` is not a string.
        """

    registered_lists = Set(
        title=_('Registered lists'),
        description=_(
            'All mailing lists with status `MailingListStatus.REGISTERED`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)

    approved_lists = Set(
        title=_('Approved lists'),
        description=_(
            'All mailing lists with status `MailingListStatus.APPROVED`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)

    modified_lists = Set(
        title=_('Modified lists'),
        description=_(
            'All mailing lists with status `MailingListStatus.MODIFIED`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)

    deactivated_lists = Set(
        title=_('Deactivated lists'),
        description=_(
            'All mailing lists with status `MailingListStatus.DEACTIVATING`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)
