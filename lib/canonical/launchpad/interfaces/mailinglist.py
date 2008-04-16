# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Mailing list interfaces."""

__metaclass__ = type
__all__ = [
    'CannotChangeSubscription',
    'CannotSubscribe',
    'CannotUnsubscribe',
    'IMailingList',
    'IMailingListAPIView',
    'IMailingListApplication',
    'IMailingListSet',
    'IMailingListSubscription',
    'IMessageApproval',
    'IMessageApprovalSet',
    'MailingListAutoSubscribePolicy',
    'MailingListStatus',
    'PostedMessageStatus',
    ]


from zope.interface import Interface
from zope.schema import Choice, Datetime, Object, Set, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.interfaces import IEmailAddress
from canonical.launchpad.interfaces.message import IMessage
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication
from canonical.lazr.enum import DBEnumeratedType, DBItem


class IMailingListApplication(ILaunchpadApplication):
    """Mailing lists application root."""


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

    UPDATING = DBItem(9, """
        Updating

        A modified mailing list is being updated by Mailman.
        """)

    DEACTIVATING = DBItem(10, """
        Deactivating

        The mailing list has been flagged for deactivation by the team owner.
        Mailman will be informed of this and will take the necessary actions
        to deactive the list.
        """)

    MOD_FAILED = DBItem(11, """
        Modification failed

        Mailman was unsuccessful in modifying the mailing list.
        """)


class MailingListAutoSubscribePolicy(DBEnumeratedType):
    """A person's auto-subscription policy.

    When a person joins a team, or is joined to a team, their
    auto-subscription policy describes how and whether they will be
    automatically subscribed to any team mailing list that the team may have.

    This does not describe what happens when a team that already has members
    gets a new team mailing list.  In that case, its members are never
    automatically subscribed to the mailing list.
    """

    NEVER = DBItem(0, """
        Never subscribe automatically

        The user must explicitly subscribe to a team mailing list for any team
        that she joins.
        """)

    ON_REGISTRATION = DBItem(1, """
        Subscribe on self-registration

        The user is automatically joined to any team mailng list for a team
        that she joins explicitly.  She is never joined to any team mailing
        list for a team that someone else joins her to.
        """)

    ALWAYS = DBItem(2, """
        Always subscribe automatically

        The user is automatically subscribed to any team mailing list when she
        is added to the team, regardless of who joins her to the team.
        """)


class PostedMessageStatus(DBEnumeratedType):
    """The status of a posted message.

    When a message posted to a mailing list is subject to first-post
    moderation, the message gets one of these statuses.
    """

    NEW = DBItem(0, """
        New status

        The message has been posted and held for first-post moderation, but no
        disposition of the message has yet been made.
        """)

    APPROVAL_PENDING = DBItem(20, """
        Approval pending

        The team administrator has approved this message, but Mailman has not
        yet been informed of this status.
        """)

    REJECTION_PENDING = DBItem(30, """
        Decline pending

        The team administrator has declined this message, but Mailman has not
        yet been informed of this status.
        """)

    APPROVED = DBItem(40, """
        Approved

        A message held for first-post moderation has been approved.
        """)

    REJECTED = DBItem(50, """
        Rejected

        A message held for first-post moderation has been rejected.
        """)

    DISCARD_PENDING = DBItem(60, """
        Discard pending

        The team administrator has discarded this message, but Mailman has not
        yet been informed of this status.
        """)

    DISCARDED = DBItem(70, """
        Discarded

        A message held for first-post moderation has been discarded.
        """)


class IMailingList(Interface):
    """A mailing list."""

    team = PublicPersonChoice(
        title=_('Team'),
        description=_('The team that this mailing list is associated with.'),
        vocabulary='ValidTeam',
        required=True, readonly=True)

    registrant = PublicPersonChoice(
        title=_('Registrant'),
        description=_('The person who registered the mailing list.'),
        vocabulary='ValidPersonOrTeam',
        required=True, readonly=True)

    date_registered = Datetime(
        title=_('Registration date'),
        description=_('The date on which this mailing list was registered.'),
        required=True, readonly=True)

    reviewer = PublicPersonChoice(
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
        description=_('Any instructions or links that should be sent to new '
                      'subscribers to this mailing list.'),
        required=False,
        )

    address = TextLine(
        title=_("This list's email address."),
        description=_(
            "The text representation of this team's email address."),
        required=True,
        readonly=True)

    archive_url = TextLine(
        title=_("The url to the list's archives"),
        description=_(
            'This is the url to the archive if the mailing list has ever '
            'activated.  Such a list, even if now inactive, may still have '
            'an archive.  If the list has never been activated, this will '
            'be None.'),
        readonly=True)

    def isUsable():
        """Is this mailing list in a state to accept messages?

        This doesn't neccessarily mean that the list is in perfect
        shape: its status might be `MailingListStatus.MOD_FAILED`. But
        it should be able to handle messages.
        """

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

    def startUpdating():
        """Set the status to the `MailingListStatus.UPDATING` state.

        This state change happens when Mailman pulls the list of modified
        mailing lists and begins updating them.

        :raises AssertionError: When prior to updating, the status if the
            mailing list is not `MailingListStatus.MODIFIED`.
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

    def reactivate():
        """Reactivate the mailing list.

        This sets the status to `MailingListStatus.APPROVED`.

        :raises AssertionError: When prior to reactivation, the status of the
            mailing list is not `MailingListStatus.INACTIVE`.
        """

    def cancelRegistration():
        """Delete this mailing list from the database.

        Only mailing lists in the REGISTERED state can be deleted.
        """

    def getSubscription(person):
        """Get a person's subscription details for the mailing list.

        :param person: The person whose subscription details to get.

        :return: If the person is subscribed to this mailing list, an
                 IMailingListSubscription. Otherwise, None.
        """

    def subscribe(person, address=None):
        """Subscribe a person to the mailing list.

        :param person: The person to subscribe to the mailing list.  The
            person must be a member (either direct or indirect) of the team
            linked to this mailing list.
        :param address: The `IEmailAddress` to use for the subscription.  The
            address must be owned by `person`.  If None (the default), then
            the person's preferred email address is used.  If the person's
            preferred address changes, their subscription address will change
            as well.
        :raises CannotSubscribe: Raised when the person is not allowed to
            subscribe to the mailing list with the given address.  For
            example, this is raised when the person is not a member of the
            team linked to this mailing list, when `person` is a team, or when
            `person` does not own the given email address.
        """

    def unsubscribe(person):
        """Unsubscribe the person from the mailing list.

        :param person: A member of the mailing list.
        :raises CannotUnsubscribe: Raised when the person is not a member of
            the mailing list.
        """

    def changeAddress(person, address):
        """Change the address a person is subscribed with.

        :param person: The mailing list subscriber.
        :param address: The new IEmailAddress to use for the subscription.
            The address must be owned by `person`.  If None, the person's
            preferred email address is used.  If the person's preferred
            address changes, their subscription address will change as well.
        :raises CannotChangeSubscription: Raised when the person is not a
            allowed to change their subscription address.  For example, this
            is raised when the person is not a member of the team linked to
            this mailing list, when `person` is a team, or when `person` does
            not own the given email address.
        """

    def getSubscribedAddresses():
        """Return the set of subscribed email addresses for members.

        :return: an iterator over the subscribed IEmailAddresses for all
            subscribed members of the mailing list, in no particular order.
            This represents all the addresses which will receive messages
            posted to the mailing list.
        """

    def getSenderAddresses():
        """Return the set of all email addresses for members.

        :return: an iterator over the all the registered and validated
            IEmailAddresses for all subscribed members of the mailing list, in
            no particular order.  These represent all the addresses which are
            allowed to post to the mailing list.
        """

    def holdMessage(message):
        """Hold a message for approval on this mailing list.

        :param message: The IMessage to hold.
        :return: The IMessageApproval representing the held message.
        """

    def getReviewableMessages():
        """Return the set of all held messages for this list requiring review.

        :return: A sequence of `IMessageApproval`s for this mailing list,
            where the status is `PostedMessageStatus.NEW`.  The returned set
            is ordered first by the date the message was posted, then by
            Message-ID.
        """


class IMailingListSet(Interface):
    """A set of mailing lists."""

    title = TextLine(
        title=_('Title'),
        description=_('The hard coded title.'),
        readonly=True)

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

    active_lists = Set(
        title=_('Active lists'),
        description=_(
            'All mailing lists with status `MailingListStatus.ACTIVE`.'),
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
        description=_('All mailing lists with status '
                      '`MailingListStatus.DEACTIVATING`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)

    unsynchronized_lists = Set(
        title=_('Unsynchronized lists'),
        description=_(
            'All mailing lists with unsynchronized state, e.g. '
            '`MailingListStatus.CONSTRUCTING` and '
            '`MailingListStatus.UPDATING`.'),
        value_type=Object(schema=IMailingList),
        readonly=True)


class IMailingListAPIView(Interface):
    """XMLRPC API that Mailman polls for mailing list actions."""

    def getPendingActions():
        """Get all pending mailing list actions.

        In addition, any mailing list for which there are actions pending will
        have their states transitioned to the next node in the workflow.  For
        example, an APPROVED mailing list will be transitioned to
        CONSTRUCTING, and a MODIFIED mailing list will be transitioned to
        UPDATING.

        :return: A dictionary with keys being the action names and values
            being a sequence of values describing the details of each action.

        Actions are strings, with the following valid values:

        * 'create'     -- create the named team mailing list
        * 'deactivate' -- deactivate the named team mailing list
        * 'modify'     -- modify an existing team mailing list

        For the 'deactivate' action, the value items are just the team name
        for the list being deactivated.  For the 'create' and 'modify'
        actions, the value items are 2-tuples where the first item is the team
        name and the second item is a dictionary of the list attributes to
        modify, for example 'welcome_message'.

        There will be at most one action per team.
        """

    def reportStatus(statuses):
        """Report the status of mailing list actions.

        When Mailman processes the actions requested in getPendingActions(),
        it will report the status of those actions back to Launchpad.

        In addition, any mailing list for which a status is being reported
        will have its state transitioned to the next node in the workflow.
        For example, a CONSTRUCTING or UPDATING mailing list will be
        transitioned to ACTIVE or FAILED depending on the status.

        :param statuses: A dictionary mapping team names to result strings.
            The result strings may be either 'success' or 'failure'.
        """

    def getMembershipInformation(teams):
        """Get membership information for the listed teams.

        :param teams: The list of team names for which Mailman is requesting
            membership information.
        :return: A data structure representing the requested information.  See
            below for the format of that data structure.  The records in
            values are sorted by email address.

        The return value is of the format:

        {team_name: [(address, realname, flags, status), ...], ...}

        And each value contains an entry for all addresses that are subscribed
        to the mailing list linked to the named team.
        """

    def isRegisteredInLaunchpad(address):
        """Whether the address is a Launchpad member.

        :param address: The text email address to check.
        :return: True if the address is a validated or preferred email address
            owned by a Launchpad member.
        """

    def inGoodStanding(address):
        """Whether the address is a Launchpad member in good standing.

        :param address: The text email address to check.
        :return: True if the address is a member of Launchpad in good or
            better standing (e.g. GOOD or EXCELLENT).  False is returned if
            the address is not registered in Launchpad, or is assigned to a
            team.
        """

    def holdMessage(team_name, text):
        """Hold the message for approval though the Launchpad u/i.

        :param team_name: The name of the team/mailing list that this message
            was posted to.
        :param text: The original text of the message.
        :return: True
        """

    def getMessageDispositions():
        """Get all new message dispositions.

        This returns a dictionary mapping message ids to their disposition,
        which will either be 'accept', 'decline' or 'discard'.  This only
        returns message-ids of disposed messages since the last time this
        method was called.  Because this also acknowledges the pending states
        of such messages, it changes the state on the Launchpad server.

        :return: A dictionary mapping message-ids to the disposition tuple.
            This tuple is of the form (team-name, action), where the action is
            either the string 'accept' or 'decline'.
        """


class IMailingListSubscription(Interface):
    """A mailing list subscription."""

    person = PublicPersonChoice(
        title=_('Person'),
        description=_('The person who is subscribed to this mailing list.'),
        vocabulary='ValidTeamMember',
        required=True, readonly=True)

    mailing_list = Choice(
        title=_('Mailing list'),
        description=_('The mailing list for this subscription.'),
        vocabulary='ActiveMailingList',
        required=True, readonly=True)

    date_joined = Datetime(
        title=_('Date joined'),
        description=_("The date this person joined the team's mailing list."),
        required=True, readonly=True)

    email_address = Object(
        schema=IEmailAddress,
        title=_('Email address'),
        description=_(
            "The subscribed email address or None, meaning use the person's "
            'preferred email address, even if that changes.'),
        required=True)

    subscribed_address = Object(
        schema=IEmailAddress,
        title=_('Email Address'),
        description=_('The IEmailAddress this person is subscribed with.'),
        readonly=True)


class IMessageApproval(Interface):
    """A held message."""

    message_id = Text(
        title=_('Message-ID'),
        description=_('The RFC 2822 Message-ID header.'),
        required=True, readonly=True)

    posted_by = PublicPersonChoice(
        title=_('Posted by'),
        description=_('The Launchpad member who posted the message.'),
        vocabulary='ValidPersonOrTeam',
        required=True, readonly=True)

    posted_message = Object(
        schema=IMessage,
        title=_('Posted message'),
        description=_('The message that was posted and held.'),
        required=True, readonly=True)

    posted_date = Datetime(
        title=_('Date posted'),
        description=_('The date this message was posted.'),
        required=True, readonly=True)

    mailing_list = Object(
        schema=IMailingList,
        title=_('The mailing list'),
        description=_('The mailing list this message was posted to.'),
        required=True, readonly=True)

    status = Choice(
        title=_('Status'),
        description=_('The status of the held message.'),
        vocabulary='PostedMessageStatus',
        required=True)

    disposed_by = PublicPersonChoice(
        title=_('Approved or rejected by'),
        description=_('The person who approved or rejected this message.'),
        vocabulary='ValidPersonOrTeam',
        required=False)

    disposal_date = Datetime(
        title=_('Date approved or rejected'),
        description=_('The date this message was approved or rejected.'),
        required=False)

    def approve(reviewer):
        """Approve the message.

        Set the status to APPROVAL_PENDING, indicating that the reviewer has
        chosen to approve the message, but that Mailman has not yet
        acknowledged this disposition.

        :param reviewer: The person who did the review.
        """

    def reject(reviewer):
        """Reject the message.

        Set the status to REJECTION_PENDING, indicating that the reviewer has
        chosen to reject (i.e. bounce) the message, but that Mailman has not
        yet acknowledged this disposition.

        :param reviewer: The person who did the review.
        """

    def discard(reviewer):
        """Discard the message.

        Set the status to DISCARD_PENDING, indicating that the reviewer has
        chosen to discard the message, but that Mailman has not yet
        acknowledged this disposition.

        :param reviewer: The person who did the review.
        """

    def acknowledge():
        """Acknowledge the pending status of a message.

        This changes the statuses APPROVAL_PENDING to APPROVED,
        REJECTION_PENDING to REJECTED and DISCARD_PENDING to DISCARD.  It is
        illegal to call this function when the status is not one of these
        states.
        """


class IMessageApprovalSet(Interface):
    """Sets of held message."""

    def getMessageByMessageID(message_id):
        """Return the held message with the matching Message-ID.

        :param message_id: The RFC 2822 Message-ID header.
        :return: The matching IMessageApproval or None if no match was found.
        """

    def getHeldMessagesWithStatus(status):
        """Return a sequence of message holds matching status.

        :param status: A PostedMessageStatus enum value.
        :return: An iterator over all the matching held messages.
        """


class CannotSubscribe(Exception):
    """The subscriber is not allowed to subscribe to the mailing list.

    This is raised when the person is not allowed to subscribe to the mailing
    list with the given address.  For example, this is raised when the person
    is not a member of the team linked to this mailing list, when `person` is
    a team, or when `person` does not own the given email address.
    """

class CannotUnsubscribe(Exception):
    """The person cannot unsubscribe from the mailing list.

    This is raised when Person who is not a member of the mailing list tries
    to unsubscribe from the mailing list.
    """

class CannotChangeSubscription(Exception):
    """The subscription change cannot be fulfilled.

    This is raised when the person is not a allowed to change their
    subscription address.  For example, this is raised when the person is not
    a member of the team linked to this mailing list, when `person` is a team,
    or when `person` does not own the given email address.
    """
