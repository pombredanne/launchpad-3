# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'SimilarTicketsSearch',
    'Ticket',
    'TicketTargetSearch',
    'TicketPersonSearch',
    'TicketSet']

import operator
from email.Utils import make_msgid

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, providedBy
from zope.security.proxy import isinstance as zope_isinstance

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLRelatedJoin, SQLObjectNotFound)
from sqlobject.sqlbuilder import SQLConstant

from canonical.launchpad.interfaces import (
    IBugLinkTarget, InvalidTicketStateError, ILanguage, ILanguageSet,
    ILaunchpadCelebrities, IMessage, IPerson, ITicket, ITicketSet,
    TICKET_STATUS_DEFAULT_SEARCH)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search

from canonical.launchpad.database.buglinktarget import BugLinkTargetMixin
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.database.ticketbug import TicketBug
from canonical.launchpad.database.ticketmessage import TicketMessage
from canonical.launchpad.database.ticketsubscription import TicketSubscription
from canonical.launchpad.event import (
    SQLObjectCreatedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.webapp.snapshot import Snapshot

from canonical.lp.dbschema import (
    EnumCol, TicketAction, TicketSort, TicketStatus,
    TicketParticipation, TicketPriority, Item)


class notify_ticket_modified:
    """Decorator that sends a SQLObjectModifiedEvent after a workflow action.

    This decorator will take a snapshot of the object before the call to
    the decorated workflow_method. It will fire an
    SQLObjectModifiedEvent after the method returns.

    The list of edited_fields will be computed by comparing the snapshot
    with the modified ticket. The fields that are checked for
    modifications are: status, messages, dateanswered, answerer, answer,
    datelastquery and datelastresponse.

    The user triggering the event is taken from the returned message.
    """

    def __call__(self, func):
        """Return the decorator."""
        def notify_ticket_modified(self, *args, **kwargs):
            old_ticket = Snapshot(self, providing=providedBy(self))
            msg = func(self, *args, **kwargs)

            edited_fields = ['messages']
            for field in ['status', 'dateanswered', 'answerer', 'answer',
                          'datelastquery', 'datelastresponse']:
                if getattr(self, field) != getattr(old_ticket, field):
                    edited_fields.append(field)

            notify(SQLObjectModifiedEvent(
                self, object_before_modification=old_ticket,
                edited_fields=edited_fields, user=msg.owner))
            return msg
        return notify_ticket_modified


class Ticket(SQLBase, BugLinkTargetMixin):
    """See ITicket."""

    implements(ITicket, IBugLinkTarget)

    _defaultOrder = ['-priority', 'datecreated']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    language = ForeignKey(
        dbName='language', notNull=True, foreignKey='Language')
    status = EnumCol(
        schema=TicketStatus, notNull=True, default=TicketStatus.OPEN)
    priority = EnumCol(
        schema=TicketPriority, notNull=True, default=TicketPriority.NORMAL)
    assignee = ForeignKey(
        dbName='assignee', notNull=False, foreignKey='Person', default=None)
    answerer = ForeignKey(
        dbName='answerer', notNull=False, foreignKey='Person', default=None)
    answer = ForeignKey(dbName='answer', notNull=False,
        foreignKey='TicketMessage', default=None)
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
    messages = SQLMultipleJoin('TicketMessage', joinColumn='ticket',
        prejoins=['message'], orderBy=['datecreated', 'TicketMessage.id'])
    reopenings = SQLMultipleJoin('TicketReopening', orderBy='datecreated',
        joinColumn='ticket')

    # attributes
    @property
    def target(self):
        """See ITicket."""
        if self.product:
            return self.product
        elif self.sourcepackagename:
            return self.distribution.getSourcePackage(
                self.sourcepackagename.name)
        else:
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

    def isSubscribed(self, person):
        return bool(TicketSubscription.selectOneBy(ticket=self, person=person))

    # Workflow methods

    # The lifecycle of a support request is documented in
    # https://help.launchpad.net/SupportRequestLifeCycle, so remember
    # to update that document for any pertinent changes.
    @notify_ticket_modified()
    def setStatus(self, user, new_status, comment, datecreated=None):
        """See ITicket."""
        if new_status == self.status:
            raise InvalidTicketStateError(
                "New status is same as the old one.")

        # If the previous state recorded an answer, clear those
        # information as well.
        self.answerer = None
        self.answer = None
        self.dateanswered = None

        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=TicketAction.SETSTATUS, new_status=new_status,
            update_ticket_dates=False)

    @notify_ticket_modified()
    def addComment(self, user, comment, datecreated=None):
        """See ITicket."""
        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=TicketAction.COMMENT, new_status=self.status,
            update_ticket_dates=False)

    @property
    def can_request_info(self):
        """See ITicket."""
        return self.status in [
            TicketStatus.OPEN, TicketStatus.NEEDSINFO, TicketStatus.ANSWERED]

    @notify_ticket_modified()
    def requestInfo(self, user, question, datecreated=None):
        """See ITicket."""
        assert user != self.owner, "Owner cannot use requestInfo()."
        if not self.can_request_info:
            raise InvalidTicketStateError(
            "Ticket status != OPEN, NEEDSINFO, or ANSWERED")
        if self.status == TicketStatus.ANSWERED:
            new_status = self.status
        else:
            new_status = TicketStatus.NEEDSINFO
        return self._newMessage(
            user, question, datecreated=datecreated,
            action=TicketAction.REQUESTINFO, new_status=new_status)

    @property
    def can_give_info(self):
        """See ITicket."""
        return self.status in [TicketStatus.OPEN, TicketStatus.NEEDSINFO]

    @notify_ticket_modified()
    def giveInfo(self, reply, datecreated=None):
        """See ITicket."""
        if not self.can_give_info:
            raise InvalidTicketStateError(
                "Ticket status != OPEN or NEEDSINFO")
        return self._newMessage(
            self.owner, reply, datecreated=datecreated,
            action=TicketAction.GIVEINFO, new_status=TicketStatus.OPEN)

    @property
    def can_give_answer(self):
        """See ITicket."""
        return self.status in [
            TicketStatus.OPEN, TicketStatus.NEEDSINFO, TicketStatus.ANSWERED]

    @notify_ticket_modified()
    def giveAnswer(self, user, answer, datecreated=None):
        """See ITicket."""
        if not self.can_give_answer:
            raise InvalidTicketStateError(
            "Ticket status != OPEN, NEEDSINFO or ANSWERED")
        if self.owner == user:
            new_status = TicketStatus.SOLVED
            action = TicketAction.CONFIRM
        else:
            new_status = TicketStatus.ANSWERED
            action = TicketAction.ANSWER

        msg = self._newMessage(
            user, answer, datecreated=datecreated, action=action,
            new_status=new_status)

        if self.owner == user:
            self.dateanswered = msg.datecreated
            self.answerer = user
            self.answer = msg
            self.owner.assignKarma(
                'ticketownersolved', product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
        return msg

    @property
    def can_confirm_answer(self):
        """See ITicket."""
        if self.status not in [
            TicketStatus.OPEN, TicketStatus.ANSWERED, TicketStatus.NEEDSINFO]:
            return False

        for message in self.messages:
            if message.action == TicketAction.ANSWER:
                return True
        return False

    @notify_ticket_modified()
    def confirmAnswer(self, comment, answer=None, datecreated=None):
        """See ITicket."""
        if not self.can_confirm_answer:
            raise InvalidTicketStateError(
                "There is no answer that can be confirmed")
        if answer:
            assert answer in self.messages
            assert answer.owner != self.owner, (
                'Use giveAnswer() when solving own ticket.')

        msg = self._newMessage(
            self.owner, comment, datecreated=datecreated,
            action=TicketAction.CONFIRM,
            new_status=TicketStatus.SOLVED)
        if answer:
            self.dateanswered = msg.datecreated
            self.answerer = answer.owner
            self.answer = answer

            self.owner.assignKarma(
                'ticketansweraccepted', product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
            self.answerer.assignKarma(
                'ticketanswered', product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
        return msg

    def canReject(self, user):
        """See ITicket."""
        for contact in self.target.support_contacts:
            if user.inTeam(contact):
                return True
        admin = getUtility(ILaunchpadCelebrities).admin
        # self.target can return a source package, we want the
        # pillar target.
        context = self.product or self.distribution
        return user.inTeam(context.owner) or user.inTeam(admin)

    @notify_ticket_modified()
    def reject(self, user, comment, datecreated=None):
        """See ITicket."""
        assert self.canReject(user), (
            'User "%s" cannot reject the ticket.' % user.displayname)
        if self.status == TicketStatus.INVALID:
            raise InvalidTicketStateError("Ticket is already rejected.")
        msg = self._newMessage(
            user, comment, datecreated=datecreated,
            action=TicketAction.REJECT, new_status=TicketStatus.INVALID)
        self.answerer = user
        self.dateanswered = msg.datecreated
        self.answer = msg
        return msg

    @notify_ticket_modified()
    def expireTicket(self, user, comment, datecreated=None):
        """See ITicket."""
        if self.status not in [TicketStatus.OPEN, TicketStatus.NEEDSINFO]:
            raise InvalidTicketStateError(
                "Ticket status != OPEN or NEEDSINFO")
        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=TicketAction.EXPIRE, new_status=TicketStatus.EXPIRED)

    @property
    def can_reopen(self):
        """See ITicket."""
        return self.status in [
            TicketStatus.ANSWERED, TicketStatus.EXPIRED, TicketStatus.SOLVED]

    @notify_ticket_modified()
    def reopen(self, comment, datecreated=None):
        """See ITicket."""
        if not self.can_reopen:
            raise InvalidTicketStateError(
                "Ticket status != ANSWERED, EXPIRED or SOLVED.")
        msg = self._newMessage(
            self.owner, comment, datecreated=datecreated,
            action=TicketAction.REOPEN, new_status=TicketStatus.OPEN)
        self.answer = None
        self.answerer = None
        self.dateanswered = None
        return msg

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
        return sorted(
            direct.union(indirect), key=operator.attrgetter('displayname'))

    def getDirectSubscribers(self):
        """See ITicket."""
        return sorted(self.subscribers, key=operator.attrgetter('displayname'))

    def getIndirectSubscribers(self):
        """See ITicket."""
        subscribers = set(self.target.support_contacts)

        if self.assignee:
            subscribers.add(self.assignee)

        return sorted(subscribers, key=operator.attrgetter('displayname'))

    def _newMessage(self, owner, content, action, new_status, subject=None,
                    datecreated=None, update_ticket_dates=True):
        """Create a new TicketMessage, link it to this ticket and update
        the ticket's status to new_status.

        When update_ticket_dates is True, the ticket's datelastquery or
        datelastresponse attribute is updated to the message creation date.
        The datelastquery attribute is updated when the message owner is the
        same than the ticket owner, otherwise the datelastresponse is updated.

        :owner: An IPerson.
        :content: A string or an IMessage. When it's an IMessage, the owner
                  must be the same than the :owner: parameter.
        :action: A TicketAction.
        :new_status: A TicketStatus.
        :subject: The Message subject, default to followup_subject. Ignored
                  when content is an IMessage.
        :datecreated: A datetime object which will be used as the Message
                      creation date. Ignored when content is an IMessage.
        :update_ticket_dates: A bool.
        """
        if IMessage.providedBy(content):
            assert owner == content.owner, (
                'The IMessage has the wrong owner.')
            msg = content
        else:
            if subject is None:
                subject = self.followup_subject
            if datecreated is None:
                datecreated = UTC_NOW
            msg = Message(
                owner=owner, rfc822msgid=make_msgid('lptickets'),
                subject=subject, datecreated=datecreated)
            chunk = MessageChunk(message=msg, content=content, sequence=1)

        tktmsg = TicketMessage(
            ticket=self, message=msg, action=action, new_status=new_status)
        notify(SQLObjectCreatedEvent(tktmsg, user=tktmsg.owner))
        # make sure we update the relevant date of response or query
        if update_ticket_dates:
            if owner == self.owner:
                self.datelastquery = msg.datecreated
            else:
                self.datelastresponse = msg.datecreated
        self.status = new_status
        return tktmsg

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

    def findExpiredTickets(self, days_before_expiration):
        """See ITicketSet."""
        return Ticket.select(
            """status IN (%s, %s)
                    AND (datelastresponse IS NULL
                         OR datelastresponse < (
                            current_timestamp -interval '%s days'))
                    AND
                    datelastquery  < (current_timestamp - interval '%s days')
                    AND assignee IS NULL
            """ % sqlvalues(
                TicketStatus.OPEN, TicketStatus.NEEDSINFO,
                days_before_expiration, days_before_expiration))

    def searchTickets(self, search_text=None, language=None,
                      status=TICKET_STATUS_DEFAULT_SEARCH, sort=None):
        """See ITicketSet"""
        return TicketSearch(
            search_text=search_text, status=status, language=language,
            sort=sort).getResults()

    def getTicketLanguages(self):
        """See ITicketSet"""
        return set(Language.select('Language.id = Ticket.language',
            clauseTables=['Ticket'], distinct=True))

    @staticmethod
    def new(title=None, description=None, owner=None,
            product=None, distribution=None, sourcepackagename=None,
            datecreated=None, language=None):
        """Common implementation for ITicketTarget.newTicket()."""
        if datecreated is None:
            datecreated = UTC_NOW
        if language is None:
            language = getUtility(ILanguageSet)['en']
        ticket = Ticket(
            title=title, description=description, owner=owner,
            product=product, distribution=distribution, language=language,
            sourcepackagename=sourcepackagename, datecreated=datecreated)

        # Subscribe the submitter
        ticket.subscribe(owner)

        return ticket

    def get(self, ticket_id, default=None):
        """See ITicketSet."""
        try:
            return Ticket.get(ticket_id)
        except SQLObjectNotFound:
            return default


class TicketSearch:
    """Base object for searching tickets.

    The search parameters are specified at creation time and getResults()
    is used to retrieve the tickets matching the search criteria.
    """

    def __init__(self, search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
                 language=None, needs_attention_from=None, sort=None,
                 product=None, distribution=None, sourcepackagename=None):
        self.search_text = search_text

        if zope_isinstance(status, Item):
            self.status = [status]
        else:
            self.status = status

        if ILanguage.providedBy(language):
            self.language = [language]
        else:
            self.language = language

        self.sort = sort
        if needs_attention_from is not None:
            assert IPerson.providedBy(needs_attention_from), (
                "expected IPerson, got %r" % needs_attention_from)
        self.needs_attention_from = needs_attention_from

        self.product = product
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename

    def getTargetConstraints(self):
        """Return the constraints related to the ITicketTarget context."""
        if self.sourcepackagename:
            assert self.distribution is not None, (
                "Distribution must be specified if sourcepackage is not None")

        constraints = []

        if self.product:
            constraints.append('Ticket.product = %s' % sqlvalues(self.product))
        elif self.distribution:
            constraints.append(
                'Ticket.distribution = %s' % sqlvalues(self.distribution))
            if self.sourcepackagename:
                constraints.append(
                    'Ticket.sourcepackagename = %s' % sqlvalues(
                        self.sourcepackagename))

        return constraints

    def getTableJoins(self):
        """Return the tables that should be joined for the constraints."""
        if self.needs_attention_from:
            return self.getMessageJoins(self.needs_attention_from)
        else:
            return []

    def getMessageJoins(self, person):
        """Create the joins needed to select constraints on the messages by a
        particular person."""
        return [
            ('LEFT OUTER JOIN TicketMessage '
             'ON TicketMessage.ticket = Ticket.id'),
            ('LEFT OUTER JOIN Message ON TicketMessage.message = Message.id '
             'AND Message.owner = %s' % sqlvalues(person))]

    def getConstraints(self):
        """Return a list of SQL constraints to use for this search."""

        constraints = self.getTargetConstraints()

        if self.search_text is not None:
            constraints.append(
                'Ticket.fti @@ ftq(%s)' % quote(self.search_text))

        if self.status:
            constraints.append('Ticket.status IN %s' % sqlvalues(
                list(self.status)))

        if self.needs_attention_from:
            constraints.append('''(
                (Ticket.owner = %(person)s
                    AND Ticket.status IN %(owner_status)s)
                OR (Ticket.owner != %(person)s AND
                    Ticket.status = %(open_status)s AND
                    Message.owner = %(person)s)
                )''' % sqlvalues(
                    person=self.needs_attention_from,
                    owner_status=[
                        TicketStatus.NEEDSINFO, TicketStatus.ANSWERED],
                    open_status=TicketStatus.OPEN))

        if self.language:
            constraints.append(
                'Ticket.language IN (%s)'
                    % ', '.join(sqlvalues(*self.language)))

        return constraints

    def getPrejoins(self):
        """Return a list of tables that should be prejoined on this search."""
        # The idea is to prejoin all dependant tables, except if the
        # object will be the same in all rows because it is used as a
        # search criteria.
        if self.product or self.sourcepackagename:
            # Will always be the same product or sourcepackage.
            return ['owner']
        elif self.distribution:
            # Same distribution, sourcepackagename will vary.
            return ['owner', 'sourcepackagename']
        else:
            # TicketTarget will vary.
            return ['owner', 'product', 'distribution', 'sourcepackagename']

    def getOrderByClause(self):
        """Return the ORDER BY clause to use to order this search's results."""
        sort = self.sort
        if sort is None:
            if self.search_text:
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
            if self.search_text:
                # SQLConstant is a workaround for bug 53455
                return [SQLConstant(
                            "-rank(Ticket.fti, ftq(%s))" % quote(
                                self.search_text)),
                        "-Ticket.datecreated"]
            else:
                return "-Ticket.datecreated"
        else:
            raise AssertionError, "Unknown TicketSort value: %s" % sort

    def getResults(self):
        """Return the tickets that match this query."""
        query = ''
        constraints = self.getConstraints()
        if constraints:
            query += (
                'Ticket.id IN (SELECT Ticket.id FROM Ticket %s WHERE %s)' % (
                    '\n'.join(self.getTableJoins()),
                    ' AND '.join(constraints)))
        return Ticket.select(
            query, prejoins=self.getPrejoins(),
            orderBy=self.getOrderByClause())


class TicketTargetSearch(TicketSearch):
    """Search tickets in an ITicketTarget context.

    Used to implement ITicketTarget.search().
    """

    def __init__(self, search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
                 language=None, owner=None,  needs_attention_from=None,
                 sort=None, product=None, distribution=None,
                 sourcepackagename=None):
        assert product is not None or distribution is not None, (
            "Missing a product or distribution context.")
        TicketSearch.__init__(
            self, search_text=search_text, status=status, language=language,
            needs_attention_from=needs_attention_from, sort=sort,
            product=product, distribution=distribution,
            sourcepackagename=sourcepackagename)

        if owner:
            assert IPerson.providedBy(owner), (
                "expected IPerson, got %r" % owner)
        self.owner = owner

    def getConstraints(self):
        """See TicketSearch."""
        constraints = TicketSearch.getConstraints(self)
        if self.owner:
            constraints.append('Ticket.owner = %s' % self.owner.id)

        return constraints

    def getPrejoins(self):
        """See TicketSearch."""
        prejoins = TicketSearch.getPrejoins(self)
        if self.owner and 'owner' in prejoins:
            # Since it is constant, no need to prefetch it.
            prejoins.remove('owner')
        return prejoins


class SimilarTicketsSearch(TicketSearch):
    """Search tickets in a context using a similarity search algorithm.

    This search object is used to implement
    ITicketTarget.findSimilarTickets().
    """

    def __init__(self, title, product=None, distribution=None,
                 sourcepackagename=None):
        assert product is not None or distribution is not None, (
            "Missing a product or distribution context.")
        TicketSearch.__init__(
            self, search_text=title, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

        # Change the search text to use based on the native language
        # similarity search algorithm.
        self.search_text = nl_phrase_search(
            title, Ticket, " AND ".join(self.getTargetConstraints()))


class TicketPersonSearch(TicketSearch):
    """Search tickets which are related to a particular person.

    Used to implement IPerson.searchTickets().
    """

    def __init__(self, person, search_text=None,
                 status=TICKET_STATUS_DEFAULT_SEARCH, language=None,
                 participation=None, needs_attention=False, sort=None):
        if needs_attention:
            needs_attention_from = person
        else:
            needs_attention_from = None

        TicketSearch.__init__(
            self, search_text=search_text, status=status, language=language,
            needs_attention_from=needs_attention_from, sort=sort)

        assert IPerson.providedBy(person), "expected IPerson, got %r" % person
        self.person = person

        if not participation:
            self.participation = TicketParticipation.items
        elif zope_isinstance(participation, Item):
            self.participation = [participation]
        else:
            self.participation = participation

    def getTableJoins(self):
        """See TicketSearch."""
        joins = TicketSearch.getTableJoins(self)

        if TicketParticipation.SUBSCRIBER in self.participation:
            joins.append(
                'LEFT OUTER JOIN TicketSubscription '
                'ON TicketSubscription.ticket = Ticket.id'
                ' AND TicketSubscription.person = %s' % sqlvalues(
                    self.person))

        if TicketParticipation.COMMENTER in self.participation:
            message_joins = self.getMessageJoins(self.person)
            if not set(joins).intersection(set(message_joins)):
                joins.extend(message_joins)

        return joins

    queryByParticipationType = {
        TicketParticipation.ANSWERER: "Ticket.answerer = %s",
        TicketParticipation.SUBSCRIBER: "TicketSubscription.person = %s",
        TicketParticipation.OWNER: "Ticket.owner = %s",
        TicketParticipation.COMMENTER: "Message.owner = %s",
        TicketParticipation.ASSIGNEE: "Ticket.assignee = %s"}

    def getConstraints(self):
        """See TicketSearch."""
        constraints = TicketSearch.getConstraints(self)

        participations_filter = []
        for participation_type in self.participation:
            participations_filter.append(
                self.queryByParticipationType[participation_type] % sqlvalues(
                    self.person))

        if participations_filter:
            constraints.append('(' + ' OR '.join(participations_filter) + ')')

        return constraints
