# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Support Request ("Ticket")."""

__metaclass__ = type

__all__ = [
    'InvalidTicketStateError',
    'ITicket',
    'ITicketAddMessageForm',
    'ITicketChangeStatusForm',
    'ITicketSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import (
     Bool, Choice, Datetime,  Int, List, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.ticketmessage import ITicketMessage
from canonical.launchpad.interfaces.tickettarget import (
        TICKET_STATUS_DEFAULT_SEARCH)
from canonical.lp.dbschema import TicketStatus, TicketPriority



class InvalidTicketStateError(Exception):
    """Error raised when the ticket is in an invalid state.

    Error raised when a workflow action cannot be executed because the
    ticket is in an invalid state.
    """


class ITicket(IHasOwner):
    """A single support request, or trouble ticket."""

    id = Int(title=_('Ticket Number'), required=True, readonly=True,
        description=_("The ticket or tracking number for this support "
        "request."))
    title = TextLine(
        title=_('Summary'), required=True, description=_(
        "A one-line summary of the issue or problem."))
    description = Text(
        title=_('Description'), required=True, description=_(
        "Include as much detail as possible: what "
        u"you\N{right single quotation mark}re trying to achieve, what steps "
        "you take, what happens, and what you think should happen instead."))
    status = Choice(
        title=_('Status'), vocabulary='TicketStatus',
        default=TicketStatus.OPEN, readonly=True)
    priority = Choice(
        title=_('Priority'), vocabulary='TicketPriority',
        default=TicketPriority.NORMAL)
    # XXX flacoste 2006/10/28 It should be more precise to define a new
    # vocabulary that excludes the English variants.
    language = Choice(
        title=_('Language'), vocabulary='LanguageVocabulary',
        description=_('The language in which this request is written.'))
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    assignee = Choice(title=_('Assignee'), required=False,
        description=_("The person responsible for helping to resolve the "
        "support request."),
        vocabulary='ValidPersonOrTeam')
    answerer = Choice(title=_('Answered By'), required=False,
        description=_("The person who last provided a response intended to "
        "resolve the support request."),
        vocabulary='ValidPersonOrTeam')
    answer = Object(title=_('Answer'), required=False,
        description=_("The TicketMessage that contains the answer confirmed "
            "by the owner as providing a solution to his problem."),
            schema=ITicketMessage)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    datedue = Datetime(
        title=_('Date Due'), required=False, default=None,
        description=_("The date by which we should have resolved this support "
        "request."))
    datelastquery = Datetime(title=_("Date Last Queried"), required=True,
        description=_("The date on which we last heard from the "
        "customer (owner)."))
    datelastresponse = Datetime(title=_("Date last Responded"),
        required=False,
        description=_("The date on which we last communicated "
        "with the customer. The combination of datelastquery and "
        "datelastresponse tells us in whose court the ball is."))
    dateanswered = Datetime(title=_("Date Answered"), required=False,
        description=_(
            "The date on which the ticket owner confirmed that the ticket is "
            "Solved."))
    product = Choice(title=_('Upstream Product'), required=False,
        vocabulary='Product', description=_('Select the upstream product '
        'with which you need support.'))
    distribution = Choice(title=_('Distribution'), required=False,
        vocabulary='Distribution', description=_('Select '
        'the distribution for which you need support.'))
    sourcepackagename = Choice(title=_('Source Package'), required=False,
        vocabulary='SourcePackageName', description=_('The source package '
        'in the distribution which contains the software with which you '
        'are experiencing difficulties.'))
    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_('Up-to-date notes on the status of the request.'))
    # other attributes
    target = Attribute('The ITicketTarget that is associated to this ticket.')

    # joins
    subscriptions = Attribute('The set of subscriptions to this ticket.')
    reopenings = Attribute("Records of times when this was reopened.")
    messages = List(
        title=_("Messages"),
        description=_(
            "The list of messages that were exchanged as part of this support"
            " request, sorted from first to last."),
        value_type=Object(schema=ITicketMessage),
        required=True, default=[], readonly=True)

    # Workflow methods
    def setStatus(user, new_status, comment, datecreated=None):
        """Change the status of this ticket.

        Set the ticket's status to new_status and add an ITicketMessage
        with action SETSTATUS.

        Only the ticket target owner or admin can change the status using
        this method.

        An InvalidTicketStateError is raised when this method is called
        with new_status equals to the current ticket status.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: The IPerson making the change.
        :new_status: The new TicketStatus
        :comment: A string or IMessage containing an explanation for the
                  change.
        :datecreated: Date for the message. Defaults to the current time.
        """

    can_request_info = Attribute(
        'Whether the ticket is in a state where a user can request more '
        'information from the ticket owner.')

    def requestInfo(user, question, datecreated=None):
        """Request more information from the ticket owner.

        Add an ITicketMessage with action REQUESTINFO containing the question.
        The ticket's status is changed to NEEDSINFO, and the
        datelastresponse attribute is updated to the message creation date.

        The user requesting more information cannot be the ticket's owner.
        This workflow method should only be called when the ticket status is
        OPEN or NEEDSINFO. An InvalidTicketStateError is raised otherwise.

        It can also be called when the ticket is in the ANSWERED state, but
        in that case, the status will stay unchanged.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: IPerson requesting for the information.
        :question: A string or IMessage containing the question.
        :datecreated: Date for the answer. Defaults to the current time.
        """

    can_give_info = Attribute(
        'Whether the ticket is in a state where the ticket owner can '
        'give more information on the ticket owner.')

    def giveInfo(reply, datecreated=None):
        """Reply to the information request.

        Add an ITicketMessage with action GIVEINFO. The ticket status is
        changed to OPEN, the datelastquery attribute is updated to the
        message creation time.

        This method should only be called on behalf of the ticket owner when
        the ticket is in the OPEN or NEEDSINFO state. An
        InvalidTicketStateError is raised otherwise.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :reply: A string or IMessage containing the new information.
        :datecreated: Date for the message. Defaults to the current time.
        """

    can_give_answer = Attribute(
        'Whether the ticket is in a state a user can provide an answer on '
        'the ticket.')

    def giveAnswer(user, answer, datecreated=None):
        """Give an answer to this ticket.

        If the user is not the ticket's owner, add an ITicketMessage with
        action ANSWER containing an answer for the support request. This
        changes the ticket's status to ANSWERED and updates the
        datelastresponse attribute to the message's creation date.

        When the ticket owner answers the ticket, add an ITicketMessage with
        action CONFIRM. The ticket status is changed to SOLVED, the answerer
        attribute is updated to contain the ticket owner, the answer attribute
        will be updated to point at the new message, the datelastresponse and
        dateanswered attributes are updated to the message creation date.

        This workflow method should only be called when the ticket status is
        one of OPEN, ANSWERED or NEEDSINFO. An InvalidTicketStateError is
        raised otherwise.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: IPerson giving the answer.
        :answer: A string or IMessage containing the answer.
        :datecreated: Date for the message. Defaults to the current time.
        """

    can_confirm_answer = Attribute(
        'Whether the ticket is in a state where the ticket owner to confirm '
        'that an answer solved his problem.')

    def confirmAnswer(comment, answer=None, datecreated=None):
        """Confirm that a solution to the support request was found.

        Add an ITicketMessage with action CONFIRM. The ticket status is
        changed to SOLVED. If the answer parameter is not None, it is recorded
        in the answer attribute and the answerer attribute is set to that
        message's owner. The datelastresponse and dateanswered attributes are
        updated to the message creation date.

        This workflow method should only be called on behalf of the ticket
        owner, when the ticket status is ANSWERED, or when the status is
        OPEN or NEEDSINFO but an answer was already provided. An
        InvalidTicketStateError is raised otherwise.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

       :comment: A string or IMessage containing a comment.
        :answer: The ITicketMessage that contain the answer to the support
                 request. It must be one of the ITicketMessage of this ticket.
        :datecreated: Date for the message. Defaults to the current time.
        """

    def canReject(user):
        """Test if a user can reject the ticket.

        Return true only if user is a support contact for the ticket target,
        the ticket target owner or part of the administration team.
        """

    def reject(user, comment, datecreated=None):
        """Mark this ticket as INVALID.

        Add an ITicketMessage with action REJECT. The ticket status is changed
        to INVALID. The created message is set as the ticket answer and its
        owner as the ticket answerer. The datelastresponse and dateanswered
        are updated to the message creation.

        Only support contacts for the ticket target, the target owner or a
        member of the admin team can reject a request. All tickets can be
        rejected.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: The user rejecting the request.
        :comment: A string or IMessage containing an explanation of the
                  rejection.
        :datecreated: Date for the message. Defaults to the current time.
        """

    def expireTicket(user, comment, datecreated=None):
        """Mark a ticket as EXPIRED.

        Add an ITicketMessage with action EXPIRE. This changes the ticket
        status to EXPIRED and update the datelastresponse attribute to the new
        message creation date.

        This workflow method should only be called when the ticket status is
        one of OPEN or NEEDSINFO. An InvalidTicketStateError is raised
        otherwise.

        Return the created ITicketMessage.

        (Not this method is named expireTicket and not expire because of
        conflicts with SQLObject.)

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: IPerson expiring the request.
        :comment: A string or IMessage containing an explanation for the
                  expiration.
        :datecreated: Date for the message. Defaults to the current time.
        """

    can_reopen = Attribute(
        'Whether the ticket state is a state where the ticket owner could '
        'reopen it.')

    def reopen(comment, datecreated=None):
        """Reopen a ticket that was ANSWERED, EXPIRED or SOLVED.

        Add an ITicketMessage with action REOPEN. This changes the ticket
        status to OPEN and update the datelastquery attribute to the new
        message creation date. When the ticket was in the SOLVED state, this
        method should reset the dateanswered, answerer and answer attributes.

        This workflow method should only be called on behalf of the ticket
        owner, when the ticket status is in one of ANSWERED, EXPIRED or
        SOLVED. An InvalidTicketStateError is raised otherwise.

        Return the created ITicketMessage.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :comment: A string or IMessage containing more information about the
                  request.
        :datecreated: Date for the message. Defaults to the current time.
        """

    def addComment(user, comment, datecreated=None):
        """Add a comment on the ticket.

        Create an ITicketMessage with action COMMENT. It leaves the ticket
        status unchanged.

        This method should fire an ISQLObjectCreatedEvent for the created
        ITicketMessage and an ISQLObjectModifiedEvent for the ticket.

        :user: The IPerson making the comment.
        :comment: A string or IMessage containing the comment.
        :datecreated: Date for the message. Defaults to the current time.
        """

    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the ticket."""

    def isSubscribed(person):
        """Return a boolean indicating whether the person is subscribed."""

    def unsubscribe(person):
        """Remove the person's subscription to this ticket."""

    def getSubscribers():
        """Return a list of Person that should be notified of changes to this
        ticket. That is the union of getDirectSubscribers() and
        getIndirectSubscribers().
        """

    def getDirectSubscribers():
        """Return the set of persons who are subscribed to this ticket."""

    def getIndirectSubscribers():
        """Return the set of persons who are implicitely subscribed to this
        ticket. That will be include the support contacts for the ticket's
        target as well as the ticket's assignee.
        """


class ITicketSet(Interface):
    """A container for tickets."""

    title = Attribute('Title')

    def get(ticket_id, default=None):
        """Return the ticket with the given id.

        Return :default: if no such ticket exists.
        """

    def findExpiredTickets(days_before_expiration):
        """Return the tickets that are expired.

        This should return all the tickets in the Open or Needs information
        state, without an assignee, that didn't receive any new comments in
        the last <days_before_expiration> days.
        """

    def searchTickets(search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
                      sort=None):
        """Search tickets in any context.

        :search_text: A string that is matched against the ticket
        title and description. If None, the search_text is not included as
        a filter criteria.

        :status: A sequence of TicketStatus Items. If None or an empty
        sequence, the status is not included as a filter criteria.

        :sort:  An attribute of TicketSort. If None, a default value is used.
        When there is a search_text value, the default is to sort by RELEVANCY,
        otherwise results are sorted NEWEST_FIRST.
        """


# These schemas are only used by browser/ticket.py and should really live
# there. See Bug #66950.

class ITicketAddMessageForm(Interface):
    """Form schema for adding a message to a ticket.

    This will usually includes a status change as well.
    """

    message = Text(title=_('Message'), required=False)

    subscribe_me = Bool(
        title=_('E-mail me future discussion about this request'),
        required=False, default=False)


class ITicketChangeStatusForm(Interface):
    """Form schema for changing the status of a ticket."""

    status = Choice(
        title=_('Status'), description=_('Select the new ticket status.'),
        vocabulary='TicketStatus', required=True)

    message = Text(
        title=_('Message'),
        description=_('Enter an explanation for the status change'),
        required=True)
