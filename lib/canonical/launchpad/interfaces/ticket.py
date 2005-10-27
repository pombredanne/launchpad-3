# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Support Request ("Ticket")."""

__metaclass__ = type

__all__ = [
    'ITicket',
    'ITicketSet',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine

from canonical.launchpad.interfaces import IHasOwner, IMessageTarget
from canonical.lp.dbschema import TicketStatus, TicketPriority


_ = MessageIDFactory('launchpad')


class ITicket(IHasOwner, IMessageTarget):
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
        title=_('Status'), vocabulary='TicketStatus', default=TicketStatus.NEW)
    priority = Choice(
        title=_('Priority'), vocabulary='TicketPriority',
        default=TicketPriority.NORMAL)
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
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    dateaccepted = Datetime(
        title=_('Date Accepted'), required=False, default=None)
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
        description=_("The date on which we submitted a message that "
        "we believe answers the support problem. The customer will need to "
        "verify that, and close the ticket."))
    dateclosed = Datetime(title=_("Date Closed"), required=False,
        description=_("The date on which the customer confirmed that "
        "the answers provided were sufficient to resolve the issue."))
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
    target = Attribute('The product or distribution to which this ticket '
        'belongs.')
    can_be_reopened = Attribute('Whether the ticket is in a state '
        'that can be "re-opened".')
    can_be_rejected = Attribute('Whether the ticket can be rejected.')
    is_resolved = Attribute("Whether the ticket is resolved.")
    # joins
    subscriptions = Attribute('The set of subscriptions to this ticket.')
    bugs = Attribute('Bugs related to this ticket')
    specifications = Attribute("Specifications related to this support "
        "request.")
    reopenings = Attribute("Records of times when this was reopened.")

    # workflow
    def mark_resolved(person):
        """Indicate that the person thinks this ticket is resolved.

        Depending on whether this is the requestor (owner) or someone else,
        it will affect the status in different ways. When the owner says it
        is resolved, we mark it as 'closed'. When someone else says it is
        resolved, we mark it as 'answered.'
        """

    def accept():
        """Mark this ticket as accepted.
        
        This can only be done to NEW tickets. It will usually be done when
        the first message for the ticket is received from someone other than
        the requestor (owner).  Doing so will also set the dateaccepted.
        """

    def reject(rejector):
        """Mark this ticket as rejected.
        
        This can only be done to tickets that are not CLOSED or ANSWERED. It
        will remember the dateclosed (rejection is the same as closing,
        effectively). It will also store this as the dateanswered, and it
        will remember the person who rejected it as the answerer.

        Returns True if the ticket was actually, rejected, False if for some
        reason no rejection happened (for example, it was already OPEN).
        """

    def reopen(reopener):
        """Open a ticket that has formerly been closed, or rejected."""


    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the ticket."""
        
    def unsubscribe(person):
        """Remove the person's subscription to this ticket."""

    # bug linking
    def linkBug(bug_number):
        """Link this ticket to the given bug number, returning the
        TicketBug.
        """

    def unLinkBug(bug_number):
        """Remove any link to this bug number."""


# Interfaces for containers
class ITicketSet(Interface):
    """A container for tickets."""

    title = Attribute('Title')

    latest_tickets = Attribute("The 10 most recently created support "
        "requests in Launchpad.")

    def new(title=None, description=None, owner=None, product=None,
        distribution=None):
        """Create a new trouble ticket."""

    def getAnsweredTickets():
        """Return all tickets with the status ANSWERED."""

