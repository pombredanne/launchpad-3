# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Ticket', 'TicketSet']

import operator
from email.Utils import make_msgid

from zope.event import notify
from zope.interface import implements
from zope.security.proxy import isinstance as zope_isinstance

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLRelatedJoin, SQLObjectNotFound)
from sqlobject.sqlbuilder import SQLConstant

from canonical.launchpad.interfaces import (
    IBugLinkTarget, IPerson, ITicket, ITicketSet,
    TICKET_STATUS_DEFAULT_SEARCH)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search

from canonical.launchpad.database.buglinktarget import BugLinkTargetMixin
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.database.ticketbug import TicketBug
from canonical.launchpad.database.ticketmessage import TicketMessage
from canonical.launchpad.database.ticketreopening import TicketReopening
from canonical.launchpad.database.ticketsubscription import TicketSubscription
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.helpers import check_permission

from canonical.lp.dbschema import (
    EnumCol, Item, TicketSort, TicketStatus, TicketParticipation,
    TicketPriority)


class Ticket(SQLBase, BugLinkTargetMixin):
    """See ITicket."""

    implements(ITicket, IBugLinkTarget)

    _defaultOrder = ['-priority', 'datecreated']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    status = EnumCol(
        schema=TicketStatus, notNull=True, default=TicketStatus.OPEN)
    priority = EnumCol(
        schema=TicketPriority, notNull=True, default=TicketPriority.NORMAL)
    assignee = ForeignKey(
        dbName='assignee', notNull=False, foreignKey='Person', default=None)
    answerer = ForeignKey(
        dbName='answerer', notNull=False, foreignKey='Person', default=None)
    language = ForeignKey(
        dbName='language', notNull=True, foreignKey='Language')
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    datedue = UtcDateTimeCol(notNull=False, default=None)
    datelastquery = UtcDateTimeCol(notNull=True, default=DEFAULT)
    datelastresponse = UtcDateTimeCol(notNull=False, default=None)
    dateanswered = UtcDateTimeCol(notNull=False, default=None)
    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    whiteboard = StringCol(notNull=False, default=None)

    # useful joins
    subscriptions = SQLMultipleJoin('TicketSubscription',
        joinColumn='ticket', orderBy='id')
    subscribers = SQLRelatedJoin('Person',
        joinColumn='ticket', otherColumn='person',
        intermediateTable='TicketSubscription', orderBy='name')
    bug_links = SQLMultipleJoin('TicketBug', joinColumn='ticket',
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

        if self.answerer != self.owner:
            acceptor.assignKarma(
                'ticketansweraccepted', product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
            self.answerer.assignKarma(
                'ticketanswered', product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
        else:
            # The owner is the only person who commented on this
            # ticket, so there's no point in giving him karma.
            pass
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

    def getSubscribers(self):
        """See ITicket."""
        direct = set(self.getDirectSubscribers())
        indirect = set(self.getIndirectSubscribers())
        return sorted(direct.union(indirect), key=operator.attrgetter('name'))

    def getDirectSubscribers(self):
        """See ITicket."""
        return self.subscribers

    def getIndirectSubscribers(self):
        """See ITicket."""
        support_contacts = set(self.target.support_contacts)
        if self.sourcepackagename:
            source_package = self.target.getSourcePackage(
                self.sourcepackagename.name)
            support_contacts.update(source_package.support_contacts)

        return sorted(support_contacts, key=operator.attrgetter('name'))

    def newMessage(self, owner=None, subject=None, content=None,
                   when=UTC_NOW):
        """Create a new Message and link it to this ticket."""
        msg = Message(
            owner=owner, rfc822msgid=make_msgid('lptickets'), subject=subject,
            datecreated=when)
        chunk = MessageChunk(message=msg, content=content, sequence=1)
        tktmsg = TicketMessage(ticket=self, message=msg)
        notify(SQLObjectCreatedEvent(tktmsg))
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

    # IBugLinkTarget implementation
    def linkBug(self, bug):
        """See IBugLinkTarget."""
        # subscribe the ticket's owner to the bug
        bug.subscribe(self.owner)
        return BugLinkTargetMixin.linkBug(self, bug)

    def unlinkBug(self, bug):
        """See IBugLinkTarget."""
        buglink = BugLinkTargetMixin.unlinkBug(self, bug)
        if buglink:
            # Additionnaly, unsubscribe the ticket's owner to the bug
            bug.unsubscribe(self.owner)
        return buglink

    # Template methods for BugLinkTargetMixin
    buglinkClass = TicketBug

    def createBugLink(self, bug):
        """See BugLinkTargetMixin."""
        return TicketBug(ticket=self, bug=bug)


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
            datecreated=None, language=None):
        """Common implementation for ITicketTarget.newTicket()."""
        if datecreated is None:
            datecreated = UTC_NOW
        ticket = Ticket(
            title=title, description=description, owner=owner,
            product=product, distribution=distribution, language=language,
            sourcepackagename=sourcepackagename, datecreated=datecreated)

        # Subscribe the submitter
        ticket.subscribe(owner)

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
            constraints.append('Ticket.product = %s' % product.id)
        elif distribution:
            constraints.append('Ticket.distribution = %s' % distribution.id)
            if sourcepackagename:
                constraints.append('Ticket.sourcepackagename = %s' % sourcepackagename.id)

        return constraints

    # XXX: Should this method accept a languages argument too?
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
               sort=None, owner=None, product=None, distribution=None,
               sourcepackagename=None, languages=None):
        """Common implementation for ITicketTarget.searchTickets()."""
        constraints = TicketSet._contextConstraints(
            product, distribution, sourcepackagename)

        prejoins = ['language']
        if product:
            prejoins.append('product')
        elif distribution:
            prejoins.append('distribution')
            if sourcepackagename:
                prejoins.append('sourcepackagename')

        if owner:
            assert IPerson.providedBy(owner), (
                "expected IPerson, got %r" % owner)
            constraints.append('Ticket.owner = %s' % owner.id)

        return TicketSet._commonSearch(
            constraints, prejoins, search_text, status, sort, languages)

    @staticmethod
    def searchByPerson(
        person, search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
        participation=None, sort=None, languages=None):
        """Implementation for ITicketActor.searchTickets()."""

        if participation is None:
            participation = TicketParticipation.items
        elif zope_isinstance(participation, Item):
            participation = [participation]

        participations_filter = []
        for participation_type in participation:
            participations_filter.append(
                TicketSet.queryByParticipationType[participation_type] % {
                    'personId': person.id})

        constraints = ['Ticket.id IN (%s)' %
                       '\nUNION '.join(participations_filter)]
        prejoins = ['product', 'distribution', 'sourcepackagename']

        return TicketSet._commonSearch(
            constraints, prejoins, search_text, status, sort, languages)

    queryByParticipationType = {
        TicketParticipation.ANSWERER:
            "SELECT id FROM Ticket WHERE answerer = %(personId)s",
        TicketParticipation.SUBSCRIBER:
            "SELECT ticket FROM TicketSubscription "
            "WHERE person = %(personId)s",
        TicketParticipation.OWNER:
            "SELECT id FROM Ticket WHERE owner = %(personId)s",
        TicketParticipation.COMMENTER:
            "SELECT ticket FROM TicketMessage "
            "JOIN Message ON (message = Message.id) "
            "WHERE owner = %(personId)s",
        TicketParticipation.ASSIGNEE:
            "SELECT id FROM Ticket WHERE assignee = %(personId)s"}

    @staticmethod
    def _commonSearch(
            constraints, prejoins, search_text, status, sort, languages):
        """Implement search for the criteria common to search and
        searchByPerson.
        """
        if search_text is not None:
            constraints.append('Ticket.fti @@ ftq(%s)' % quote(search_text))

        if zope_isinstance(status, Item):
            status = [status]
        if status:
            constraints.append(
                'Ticket.status IN (%s)' % ', '.join(sqlvalues(*status)))

        if languages is not None and len(languages) > 0:
            constraints.append(
                'Ticket.language IN (%s)' % ', '.join(sqlvalues(*languages)))

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

