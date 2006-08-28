# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Ticket', 'TicketSet']

from email.Utils import make_msgid

from zope.event import notify
from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLRelatedJoin, SQLObjectNotFound)
from sqlobject.sqlbuilder import SQLConstant

from canonical.launchpad.interfaces import (
    ITicket, ITicketSet, TicketSort, TICKET_STATUS_DEFAULT_SEARCH)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search

from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.database.ticketbug import TicketBug
from canonical.launchpad.database.ticketmessage import TicketMessage
from canonical.launchpad.database.ticketreopening import TicketReopening
from canonical.launchpad.database.ticketsubscription import TicketSubscription
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.helpers import check_permission

from canonical.lp.dbschema import EnumCol, TicketStatus, TicketPriority, Item


class Ticket(SQLBase):
    """See ITicket."""

    implements(ITicket)

    _defaultOrder = ['-priority', 'datecreated']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    status = EnumCol(
        schema=TicketStatus, notNull=True, default=TicketStatus.OPEN)
    priority = EnumCol(schema=TicketPriority, notNull=True,
        default=TicketPriority.NORMAL)
    assignee = ForeignKey(dbName='assignee', notNull=False,
        foreignKey='Person', default=None)
    answerer = ForeignKey(dbName='answerer', notNull=False,
        foreignKey='Person', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    datedue = UtcDateTimeCol(notNull=False, default=None)
    datelastquery = UtcDateTimeCol(notNull=True, default=DEFAULT)
    datelastresponse = UtcDateTimeCol(notNull=False, default=None)
    dateanswered = UtcDateTimeCol(notNull=False, default=None)
    product = ForeignKey(dbName='product', foreignKey='Product',
        notNull=False, default=None)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', notNull=False, default=None)
    sourcepackagename = ForeignKey(dbName='sourcepackagename',
        foreignKey='SourcePackageName', notNull=False, default=None)
    whiteboard = StringCol(notNull=False, default=None)

    # useful joins
    subscriptions = SQLMultipleJoin('TicketSubscription',
        joinColumn='ticket', orderBy='id')
    subscribers = SQLRelatedJoin('Person',
        joinColumn='ticket', otherColumn='person',
        intermediateTable='TicketSubscription', orderBy='name')
    buglinks = SQLMultipleJoin('TicketBug', joinColumn='ticket',
        orderBy='id')
    bugs = SQLRelatedJoin('Bug', joinColumn='ticket', otherColumn='bug',
        intermediateTable='TicketBug', orderBy='id')
    messages = SQLRelatedJoin('Message', joinColumn='ticket',
        otherColumn='message',
        intermediateTable='TicketMessage', orderBy='datecreated')
    reopenings = SQLMultipleJoin('TicketReopening', orderBy='datecreated',
        joinColumn='ticket')

    # attributes
    @property
    def target(self):
        """See ITicket."""
        if self.product:
            return self.product
        return self.distribution

    @property
    def followup_subject(self):
        """See IMessageTarget."""
        if not self.messages:
            return 'Re: '+ self.title
        subject = self.messages[-1].title
        if subject[:4].lower() == 're: ':
            return subject
        return 'Re: ' + subject


    @property
    def is_resolved(self):
        """See ITicket."""
        return self.status in [TicketStatus.ANSWERED, TicketStatus.REJECTED]

    @property
    def can_be_rejected(self):
        """See ITicket."""
        return self.status not in [
            TicketStatus.ANSWERED, TicketStatus.REJECTED]

    def reject(self, rejector):
        """See ITicket."""
        if not self.can_be_rejected:
            return False
        self.dateanswered = UTC_NOW
        self.datelastresponse = UTC_NOW
        self.status = TicketStatus.REJECTED
        self.answerer = rejector
        self.dateclosed = UTC_NOW
        self.sync()
        return True

    @property
    def can_be_reopened(self):
        return self.status in [
            TicketStatus.ANSWERED, TicketStatus.REJECTED]

    def isSubscribed(self, person):
        return bool(TicketSubscription.selectOneBy(ticket=self, person=person))

    def reopen(self, reopener):
        """See ITicket."""
        if not self.can_be_reopened:
            return None
        reop = TicketReopening(ticket=self, reopener=reopener,
            answerer=self.answerer, dateanswered=self.dateanswered,
            priorstate=self.status)
        self.answerer = None
        self.status = TicketStatus.OPEN
        self.dateanswered = None
        self.sync()
        return reop

    def acceptAnswer(self, acceptor, when=None):
        """See ITicket."""
        can_accept_answer = (acceptor == self.owner or
                             check_permission('launchpad.Admin', acceptor))
        assert can_accept_answer, (
            "Only the owner or admins can accept an answer.")
        self.status = TicketStatus.ANSWERED
        if when is None:
            self.dateanswered = UTC_NOW
        else:
            self.dateanswered = when
        #XXX: Set the answer to the last, non-submitter, who commented
        #     on the ticket. This is only temporary until
        #     SupportTrackerTweaks is fully implemented, and the
        #     submitter will be able to choose who answered the ticket.
        #     -- Bjorn Tillenius, 2006-02-11
        for commenter in [message.owner for message in self.messages]:
            if commenter != self.owner:
                self.answerer = commenter
                break
        else:
            # Only the submitter commented on the ticket, set him as the
            # answerer.
            self.answerer = self.owner
        self.sync()

    # subscriptions
    def subscribe(self, person):
        """See ITicket."""
        # first see if a relevant subscription exists, and if so, update it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub
        # since no previous subscription existed, create a new one
        return TicketSubscription(ticket=self, person=person)

    def unsubscribe(self, person):
        """See ITicket."""
        # see if a relevant subscription exists, and if so, delete it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                sub.destroySelf()
                return

    def newMessage(self, owner=None, subject=None, content=None,
                   when=UTC_NOW):
        """Create a new Message and link it to this ticket."""
        msg = Message(
            owner=owner, rfc822msgid=make_msgid('lptickets'), subject=subject,
            datecreated=when)
        chunk = MessageChunk(message=msg, content=content, sequence=1)
        tktmsg = TicketMessage(ticket=self, message=msg)
        # make sure we update the relevant date of response or query
        if owner == self.owner:
            self.datelastquery = msg.datecreated
        else:
            self.datelastresponse = msg.datecreated
        self.sync()
        return msg

    def linkMessage(self, message):
        """See ITicket."""
        for msg in self.messages:
            if msg == message:
                return None
        ticket_message = TicketMessage(ticket=self, message=message)
        notify(SQLObjectCreatedEvent(ticket_message))

    # linking to bugs
    def linkBug(self, bug):
        """See ITicket."""
        # subscribe the ticket owner to the bug
        bug.subscribe(self.owner)
        # and link the bug to the ticket
        for buglink in self.buglinks:
            if buglink.bug.id == bug.id:
                return buglink
        return TicketBug(ticket=self, bug=bug)

    def unLinkBug(self, bug):
        """See ITicket."""
        # see if a relevant bug link exists, and if so, delete it
        for buglink in self.buglinks:
            if buglink.bug.id == bug.id:
                # unsubscribe the ticket owner from the bug
                bug.unsubscribe(self.owner)
                TicketBug.delete(buglink.id)
                # XXX: We shouldn't return the object that we just
                #      deleted from the db.
                #      -- Bjorn Tillenius, 2005-11-21
                return buglink


class TicketSet:
    """The set of support / trouble tickets."""

    implements(ITicketSet)

    def __init__(self):
        """See ITicketSet."""
        self.title = 'Launchpad'

    @property
    def latest_tickets(self):
        """See ITicketSet."""
        return Ticket.select(orderBy='-datecreated')[:10]

    @staticmethod
    def new(title=None, description=None, owner=None,
            product=None, distribution=None, sourcepackagename=None,
            datecreated=None):
        """Common implementation for ITicketTarget.newTicket()."""
        if datecreated is None:
            datecreated = UTC_NOW
        ticket = Ticket(
            title=title, description=description, owner=owner,
            product=product, distribution=distribution,
            sourcepackagename=sourcepackagename, datecreated=datecreated)

        support_contacts = list(ticket.target.support_contacts)
        if ticket.sourcepackagename:
            source_package = ticket.target.getSourcePackage(
                ticket.sourcepackagename.name)
            support_contacts += source_package.support_contacts

        # Subscribe the submitter and the support contacts.
        ticket.subscribe(owner)
        for support_contact in support_contacts:
            ticket.subscribe(support_contact)

        return ticket

    @staticmethod
    def _contextConstraints(product=None, distribution=None,
                            sourcepackagename=None):
        """Return the list of constraints that should be applied to limit
        searches to a given context."""
        assert product is not None or distribution is not None
        if sourcepackagename:
            assert distribution is not None

        constraints = []
        if product:
            constraints.append('Ticket.product = %d' % product.id)
        elif distribution:
            constraints.append('Ticket.distribution = %d' % distribution.id)
            if sourcepackagename:
                constraints.append('Ticket.sourcepackagename = %d' % sourcepackagename.id)

        return constraints

    @staticmethod
    def findSimilar(title, product=None, distribution=None,
                     sourcepackagename=None):
        """Common implementation for ITicketTarget.findSimilarTickets()."""
        constraints = TicketSet._contextConstraints(
            product, distribution, sourcepackagename)
        query = nl_phrase_search(title, Ticket, " AND ".join(constraints))
        return TicketSet.search(query, sort=TicketSort.RELEVANCY,
                                product=product, distribution=distribution,
                                sourcepackagename=sourcepackagename)

    @staticmethod
    def search(search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
               sort=None,
               product=None, distribution=None, sourcepackagename=None):
        """Common implementation for ITicketTarget.searchTickets()."""
        constraints = TicketSet._contextConstraints(
            product, distribution, sourcepackagename)

        prejoins = []
        if product:
            prejoins.append('product')
        elif distribution:
            prejoins.append('distribution')
            if sourcepackagename:
                prejoins.append('sourcepackagename')

        if search_text is not None:
            constraints.append('Ticket.fti @@ ftq(%s)' % quote(search_text))

        if status is None:
            status = []
        elif isinstance(status, Item):
            status = [status]
        if len(status):
            constraints.append(
                'Ticket.status IN (%s)' % ', '.join(sqlvalues(*status)))

        orderBy = TicketSet._orderByFromTicketSort(search_text, sort)

        return Ticket.select(' AND '.join(constraints), prejoins=prejoins,
                             orderBy=orderBy)

    @staticmethod
    def _orderByFromTicketSort(search_text, sort):
        if sort is None:
            if search_text:
                sort = TicketSort.RELEVANCY
            else:
                sort = TicketSort.NEWEST_FIRST
        if sort is TicketSort.NEWEST_FIRST:
            return "-Ticket.datecreated"
        elif sort is TicketSort.OLDEST_FIRST:
            return "Ticket.datecreated"
        elif sort is TicketSort.STATUS:
            return ["Ticket.status", "-Ticket.datecreated"]
        elif sort is TicketSort.RELEVANCY:
            if search_text:
                # SQLConstant is a workaround for bug 53455
                return [SQLConstant(
                            "-rank(Ticket.fti, ftq(%s))" % quote(search_text)),
                        "-Ticket.datecreated"]
            else:
                return "-Ticket.datecreated"
        else:
            raise AssertionError, "Unknown TicketSort value: %s" % sort

    def get(self, ticket_id, default=None):
        """See ITicketSet."""
        try:
            return Ticket.get(ticket_id)
        except SQLObjectNotFound:
            return default

