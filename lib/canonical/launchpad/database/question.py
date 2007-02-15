# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'SimilarQuestionsSearch',
    'Question',
    'QuestionTargetSearch',
    'QuestionPersonSearch',
    'QuestionSet']

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
    IBugLinkTarget, InvalidQuestionStateError, ILanguage, ILanguageSet,
    ILaunchpadCelebrities, IMessage, IPerson, IQuestion, IQuestionSet,
    QUESTION_STATUS_DEFAULT_SEARCH)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import (
    QuestionAction, QuestionSort, QuestionStatus,
    QuestionParticipation, QuestionPriority)

from canonical.launchpad.database.buglinktarget import BugLinkTargetMixin
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.database.questionbug import QuestionBug
from canonical.launchpad.database.questionmessage import QuestionMessage
from canonical.launchpad.database.questionsubscription import (
    QuestionSubscription)
from canonical.launchpad.event import (
    SQLObjectCreatedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.webapp.enum import Item
from canonical.launchpad.webapp.snapshot import Snapshot


class notify_question_modified:
    """Decorator that sends a SQLObjectModifiedEvent after a workflow action.

    This decorator will take a snapshot of the object before the call to
    the decorated workflow_method. It will fire an
    SQLObjectModifiedEvent after the method returns.

    The list of edited_fields will be computed by comparing the snapshot
    with the modified question. The fields that are checked for
    modifications are: status, messages, dateanswered, answerer, answer,
    datelastquery and datelastresponse.

    The user triggering the event is taken from the returned message.
    """

    def __call__(self, func):
        """Return the decorator."""
        def notify_question_modified(self, *args, **kwargs):
            old_question = Snapshot(self, providing=providedBy(self))
            msg = func(self, *args, **kwargs)

            edited_fields = ['messages']
            for field in ['status', 'dateanswered', 'answerer', 'answer',
                          'datelastquery', 'datelastresponse']:
                if getattr(self, field) != getattr(old_question, field):
                    edited_fields.append(field)

            notify(SQLObjectModifiedEvent(
                self, object_before_modification=old_question,
                edited_fields=edited_fields, user=msg.owner))
            return msg
        return notify_question_modified


class Question(SQLBase, BugLinkTargetMixin):
    """See IQuestion."""

    implements(IQuestion, IBugLinkTarget)

    _table = 'Ticket'
    _defaultOrder = ['-priority', 'datecreated']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    language = ForeignKey(
        dbName='language', notNull=True, foreignKey='Language')
    status = EnumCol(
        schema=QuestionStatus, notNull=True, default=QuestionStatus.OPEN)
    priority = EnumCol(
        schema=QuestionPriority, notNull=True, default=QuestionPriority.NORMAL)
    assignee = ForeignKey(
        dbName='assignee', notNull=False, foreignKey='Person', default=None)
    answerer = ForeignKey(
        dbName='answerer', notNull=False, foreignKey='Person', default=None)
    answer = ForeignKey(dbName='answer', notNull=False,
        foreignKey='QuestionMessage', default=None)
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
    subscriptions = SQLMultipleJoin('QuestionSubscription',
        joinColumn='question', orderBy='id')
    subscribers = SQLRelatedJoin('Person',
        joinColumn='ticket', otherColumn='person',
        intermediateTable='TicketSubscription', orderBy='name')
    bug_links = SQLMultipleJoin('QuestionBug',
        joinColumn='question', orderBy='id')
    bugs = SQLRelatedJoin('Bug', joinColumn='ticket', otherColumn='bug',
        intermediateTable='TicketBug', orderBy='id')
    messages = SQLMultipleJoin('QuestionMessage', joinColumn='question',
        prejoins=['message'], orderBy=['TicketMessage.id'])
    reopenings = SQLMultipleJoin('QuestionReopening', orderBy='datecreated',
        joinColumn='question')

    # attributes
    @property
    def target(self):
        """See IQuestion."""
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
        return bool(QuestionSubscription.selectOneBy(question=self, person=person))

    # Workflow methods

    # The lifecycle of a support request is documented in
    # https://help.launchpad.net/SupportRequestLifeCycle, so remember
    # to update that document for any pertinent changes.
    @notify_question_modified()
    def setStatus(self, user, new_status, comment, datecreated=None):
        """See IQuestion."""
        if new_status == self.status:
            raise InvalidQuestionStateError(
                "New status is same as the old one.")

        # If the previous state recorded an answer, clear those
        # information as well.
        self.answerer = None
        self.answer = None
        self.dateanswered = None

        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=QuestionAction.SETSTATUS, new_status=new_status,
            update_question_dates=False)

    @notify_question_modified()
    def addComment(self, user, comment, datecreated=None):
        """See IQuestion."""
        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=QuestionAction.COMMENT, new_status=self.status,
            update_question_dates=False)

    @property
    def can_request_info(self):
        """See IQuestion."""
        return self.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO, QuestionStatus.ANSWERED]

    @notify_question_modified()
    def requestInfo(self, user, question, datecreated=None):
        """See IQuestion."""
        assert user != self.owner, "Owner cannot use requestInfo()."
        if not self.can_request_info:
            raise InvalidQuestionStateError(
            "Question status != OPEN, NEEDSINFO, or ANSWERED")
        if self.status == QuestionStatus.ANSWERED:
            new_status = self.status
        else:
            new_status = QuestionStatus.NEEDSINFO
        return self._newMessage(
            user, question, datecreated=datecreated,
            action=QuestionAction.REQUESTINFO, new_status=new_status)

    @property
    def can_give_info(self):
        """See IQuestion."""
        return self.status in [QuestionStatus.OPEN, QuestionStatus.NEEDSINFO]

    @notify_question_modified()
    def giveInfo(self, reply, datecreated=None):
        """See IQuestion."""
        if not self.can_give_info:
            raise InvalidQuestionStateError(
                "Question status != OPEN or NEEDSINFO")
        return self._newMessage(
            self.owner, reply, datecreated=datecreated,
            action=QuestionAction.GIVEINFO, new_status=QuestionStatus.OPEN)

    @property
    def can_give_answer(self):
        """See IQuestion."""
        return self.status in [
            QuestionStatus.OPEN, QuestionStatus.NEEDSINFO, QuestionStatus.ANSWERED]

    @notify_question_modified()
    def giveAnswer(self, user, answer, datecreated=None):
        """See IQuestion."""
        if not self.can_give_answer:
            raise InvalidQuestionStateError(
            "Question status != OPEN, NEEDSINFO or ANSWERED")
        if self.owner == user:
            new_status = QuestionStatus.SOLVED
            action = QuestionAction.CONFIRM
        else:
            new_status = QuestionStatus.ANSWERED
            action = QuestionAction.ANSWER

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
        """See IQuestion."""
        if self.status not in [
            QuestionStatus.OPEN, QuestionStatus.ANSWERED, QuestionStatus.NEEDSINFO]:
            return False

        for message in self.messages:
            if message.action == QuestionAction.ANSWER:
                return True
        return False

    @notify_question_modified()
    def confirmAnswer(self, comment, answer=None, datecreated=None):
        """See IQuestion."""
        if not self.can_confirm_answer:
            raise InvalidQuestionStateError(
                "There is no answer that can be confirmed")
        if answer:
            assert answer in self.messages
            assert answer.owner != self.owner, (
                'Use giveAnswer() when solving own question.')

        msg = self._newMessage(
            self.owner, comment, datecreated=datecreated,
            action=QuestionAction.CONFIRM,
            new_status=QuestionStatus.SOLVED)
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
        """See IQuestion."""
        for contact in self.target.answer_contacts:
            if user.inTeam(contact):
                return True
        admin = getUtility(ILaunchpadCelebrities).admin
        # self.target can return a source package, we want the
        # pillar target.
        context = self.product or self.distribution
        return user.inTeam(context.owner) or user.inTeam(admin)

    @notify_question_modified()
    def reject(self, user, comment, datecreated=None):
        """See IQuestion."""
        assert self.canReject(user), (
            'User "%s" cannot reject the question.' % user.displayname)
        if self.status == QuestionStatus.INVALID:
            raise InvalidQuestionStateError("Question is already rejected.")
        msg = self._newMessage(
            user, comment, datecreated=datecreated,
            action=QuestionAction.REJECT, new_status=QuestionStatus.INVALID)
        self.answerer = user
        self.dateanswered = msg.datecreated
        self.answer = msg
        return msg

    @notify_question_modified()
    def expireQuestion(self, user, comment, datecreated=None):
        """See IQuestion."""
        if self.status not in [QuestionStatus.OPEN, QuestionStatus.NEEDSINFO]:
            raise InvalidQuestionStateError(
                "Question status != OPEN or NEEDSINFO")
        return self._newMessage(
            user, comment, datecreated=datecreated,
            action=QuestionAction.EXPIRE, new_status=QuestionStatus.EXPIRED)

    @property
    def can_reopen(self):
        """See IQuestion."""
        return self.status in [
            QuestionStatus.ANSWERED, QuestionStatus.EXPIRED, QuestionStatus.SOLVED]

    @notify_question_modified()
    def reopen(self, comment, datecreated=None):
        """See IQuestion."""
        if not self.can_reopen:
            raise InvalidQuestionStateError(
                "Question status != ANSWERED, EXPIRED or SOLVED.")
        msg = self._newMessage(
            self.owner, comment, datecreated=datecreated,
            action=QuestionAction.REOPEN, new_status=QuestionStatus.OPEN)
        self.answer = None
        self.answerer = None
        self.dateanswered = None
        return msg

    # subscriptions
    def subscribe(self, person):
        """See IQuestion."""
        # First see if a relevant subscription exists, and if so, update it.
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub
        # Since no previous subscription existed, create a new one.
        return QuestionSubscription(question=self, person=person)

    def unsubscribe(self, person):
        """See IQuestion."""
        # See if a relevant subscription exists, and if so, delete it.
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                sub.destroySelf()
                return

    def getSubscribers(self):
        """See IQuestion."""
        direct = set(self.getDirectSubscribers())
        indirect = set(self.getIndirectSubscribers())
        return sorted(
            direct.union(indirect), key=operator.attrgetter('displayname'))

    def getDirectSubscribers(self):
        """See IQuestion."""
        return sorted(self.subscribers, key=operator.attrgetter('displayname'))

    def getIndirectSubscribers(self):
        """See IQuestion."""
        subscribers = set(self.target.answer_contacts)

        if self.assignee:
            subscribers.add(self.assignee)

        return sorted(subscribers, key=operator.attrgetter('displayname'))

    def _newMessage(self, owner, content, action, new_status, subject=None,
                    datecreated=None, update_question_dates=True):
        """Create a new QuestionMessage, link it to this question and update
        the question's status to new_status.

        When update_question_dates is True, the question's datelastquery or
        datelastresponse attribute is updated to the message creation date.
        The datelastquery attribute is updated when the message owner is the
        same than the question owner, otherwise the datelastresponse is updated.

        :owner: An IPerson.
        :content: A string or an IMessage. When it's an IMessage, the owner
                  must be the same than the :owner: parameter.
        :action: A QuestionAction.
        :new_status: A QuestionStatus.
        :subject: The Message subject, default to followup_subject. Ignored
                  when content is an IMessage.
        :datecreated: A datetime object which will be used as the Message
                      creation date. Ignored when content is an IMessage.
        :update_question_dates: A bool.
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
                owner=owner, rfc822msgid=make_msgid('lpquestions'),
                subject=subject, datecreated=datecreated)
            chunk = MessageChunk(message=msg, content=content, sequence=1)

        tktmsg = QuestionMessage(
            question=self, message=msg, action=action, new_status=new_status)
        notify(SQLObjectCreatedEvent(tktmsg, user=tktmsg.owner))
        # Make sure we update the relevant date of response or query.
        if update_question_dates:
            if owner == self.owner:
                self.datelastquery = msg.datecreated
            else:
                self.datelastresponse = msg.datecreated
        self.status = new_status
        return tktmsg

    # IBugLinkTarget implementation
    def linkBug(self, bug):
        """See IBugLinkTarget."""
        # Subscribe the question's owner to the bug.
        bug.subscribe(self.owner)
        return BugLinkTargetMixin.linkBug(self, bug)

    def unlinkBug(self, bug):
        """See IBugLinkTarget."""
        buglink = BugLinkTargetMixin.unlinkBug(self, bug)
        if buglink:
            # Additionnaly, unsubscribe the question's owner to the bug
            bug.unsubscribe(self.owner)
        return buglink

    # Template methods for BugLinkTargetMixin.
    buglinkClass = QuestionBug

    def createBugLink(self, bug):
        """See BugLinkTargetMixin."""
        return QuestionBug(question=self, bug=bug)


class QuestionSet:
    """The set of questions in the Answer Tracker."""

    implements(IQuestionSet)

    def __init__(self):
        """See IQuestionSet."""
        self.title = 'Launchpad'

    def findExpiredQuestions(self, days_before_expiration):
        """See IQuestionSet."""
        return Question.select(
            """status IN (%s, %s)
                    AND (datelastresponse IS NULL
                         OR datelastresponse < (
                            current_timestamp -interval '%s days'))
                    AND
                    datelastquery  < (current_timestamp - interval '%s days')
                    AND assignee IS NULL
            """ % sqlvalues(
                QuestionStatus.OPEN, QuestionStatus.NEEDSINFO,
                days_before_expiration, days_before_expiration))

    def searchQuestions(self, search_text=None, language=None,
                      status=QUESTION_STATUS_DEFAULT_SEARCH, sort=None):
        """See IQuestionSet"""
        return QuestionSearch(
            search_text=search_text, status=status, language=language,
            sort=sort).getResults()

    def getQuestionLanguages(self):
        """See IQuestionSet"""
        return set(Language.select('Language.id = Ticket.language',
            clauseTables=['Ticket'], distinct=True))

    @staticmethod
    def new(title=None, description=None, owner=None,
            product=None, distribution=None, sourcepackagename=None,
            datecreated=None, language=None):
        """Common implementation for IQuestionTarget.newQuestion()."""
        if datecreated is None:
            datecreated = UTC_NOW
        if language is None:
            language = getUtility(ILanguageSet)['en']
        question = Question(
            title=title, description=description, owner=owner,
            product=product, distribution=distribution, language=language,
            sourcepackagename=sourcepackagename, datecreated=datecreated,
            datelastquery=datecreated)

        # Subscribe the submitter
        question.subscribe(owner)

        return question

    def get(self, question_id, default=None):
        """See IQuestionSet."""
        try:
            return Question.get(question_id)
        except SQLObjectNotFound:
            return default


class QuestionSearch:
    """Base object for searching questions.

    The search parameters are specified at creation time and getResults()
    is used to retrieve the questions matching the search criteria.
    """

    def __init__(self, search_text=None, status=QUESTION_STATUS_DEFAULT_SEARCH,
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
        """Return the constraints related to the IQuestionTarget context."""
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
                        QuestionStatus.NEEDSINFO, QuestionStatus.ANSWERED],
                    open_status=QuestionStatus.OPEN))

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
            # QuestionTarget will vary.
            return ['owner', 'product', 'distribution', 'sourcepackagename']

    def getOrderByClause(self):
        """Return the ORDER BY clause to use to order this search's results."""
        sort = self.sort
        if sort is None:
            if self.search_text:
                sort = QuestionSort.RELEVANCY
            else:
                sort = QuestionSort.NEWEST_FIRST
        if sort is QuestionSort.NEWEST_FIRST:
            return "-Ticket.datecreated"
        elif sort is QuestionSort.OLDEST_FIRST:
            return "Ticket.datecreated"
        elif sort is QuestionSort.STATUS:
            return ["Ticket.status", "-Ticket.datecreated"]
        elif sort is QuestionSort.RELEVANCY:
            if self.search_text:
                # SQLConstant is a workaround for bug 53455
                return [SQLConstant(
                            "-rank(Ticket.fti, ftq(%s))" % quote(
                                self.search_text)),
                        "-Ticket.datecreated"]
            else:
                return "-Ticket.datecreated"
        elif sort is QuestionSort.RECENT_OWNER_ACTIVITY:
            return ['-Ticket.datelastquery']
        else:
            raise AssertionError, "Unknown QuestionSort value: %s" % sort

    def getResults(self):
        """Return the questions that match this query."""
        query = ''
        constraints = self.getConstraints()
        if constraints:
            query += (
                'Ticket.id IN (SELECT Ticket.id FROM Ticket %s WHERE %s)' % (
                    '\n'.join(self.getTableJoins()),
                    ' AND '.join(constraints)))
        return Question.select(
            query, prejoins=self.getPrejoins(),
            orderBy=self.getOrderByClause())


class QuestionTargetSearch(QuestionSearch):
    """Search questions in an IQuestionTarget context.

    Used to implement IQuestionTarget.searchQuestions().
    """

    def __init__(self, search_text=None, status=QUESTION_STATUS_DEFAULT_SEARCH,
                 language=None, sort=None, owner=None,
                 needs_attention_from=None, product=None, distribution=None,
                 sourcepackagename=None):
        assert product is not None or distribution is not None, (
            "Missing a product or distribution context.")
        QuestionSearch.__init__(
            self, search_text=search_text, status=status, language=language,
            needs_attention_from=needs_attention_from, sort=sort,
            product=product, distribution=distribution,
            sourcepackagename=sourcepackagename)

        if owner:
            assert IPerson.providedBy(owner), (
                "expected IPerson, got %r" % owner)
        self.owner = owner

    def getConstraints(self):
        """See QuestionSearch."""
        constraints = QuestionSearch.getConstraints(self)
        if self.owner:
            constraints.append('Ticket.owner = %s' % self.owner.id)

        return constraints

    def getPrejoins(self):
        """See QuestionSearch."""
        prejoins = QuestionSearch.getPrejoins(self)
        if self.owner and 'owner' in prejoins:
            # Since it is constant, no need to prefetch it.
            prejoins.remove('owner')
        return prejoins


class SimilarQuestionsSearch(QuestionSearch):
    """Search questions in a context using a similarity search algorithm.

    This search object is used to implement
    IQuestionTarget.findSimilarQuestions().
    """

    def __init__(self, title, product=None, distribution=None,
                 sourcepackagename=None):
        assert product is not None or distribution is not None, (
            "Missing a product or distribution context.")
        QuestionSearch.__init__(
            self, search_text=title, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)

        # Change the search text to use based on the native language
        # similarity search algorithm.
        self.search_text = nl_phrase_search(
            title, Question, " AND ".join(self.getTargetConstraints()))


class QuestionPersonSearch(QuestionSearch):
    """Search questions which are related to a particular person.

    Used to implement IPerson.searchQuestions().
    """

    def __init__(self, person, search_text=None,
                 status=QUESTION_STATUS_DEFAULT_SEARCH, language=None,
                 sort=None, participation=None, needs_attention=False):
        if needs_attention:
            needs_attention_from = person
        else:
            needs_attention_from = None

        QuestionSearch.__init__(
            self, search_text=search_text, status=status, language=language,
            needs_attention_from=needs_attention_from, sort=sort)

        assert IPerson.providedBy(person), "expected IPerson, got %r" % person
        self.person = person

        if not participation:
            self.participation = QuestionParticipation.items
        elif zope_isinstance(participation, Item):
            self.participation = [participation]
        else:
            self.participation = participation

    def getTableJoins(self):
        """See QuestionSearch."""
        joins = QuestionSearch.getTableJoins(self)

        if QuestionParticipation.SUBSCRIBER in self.participation:
            joins.append(
                'LEFT OUTER JOIN TicketSubscription '
                'ON TicketSubscription.ticket = Ticket.id'
                ' AND TicketSubscription.person = %s' % sqlvalues(
                    self.person))

        if QuestionParticipation.COMMENTER in self.participation:
            message_joins = self.getMessageJoins(self.person)
            if not set(joins).intersection(set(message_joins)):
                joins.extend(message_joins)

        return joins

    queryByParticipationType = {
        QuestionParticipation.ANSWERER: "Ticket.answerer = %s",
        QuestionParticipation.SUBSCRIBER: "TicketSubscription.person = %s",
        QuestionParticipation.OWNER: "Ticket.owner = %s",
        QuestionParticipation.COMMENTER: "Message.owner = %s",
        QuestionParticipation.ASSIGNEE: "Ticket.assignee = %s"}

    def getConstraints(self):
        """See QuestionSearch."""
        constraints = QuestionSearch.getConstraints(self)

        participations_filter = []
        for participation_type in self.participation:
            participations_filter.append(
                self.queryByParticipationType[participation_type] % sqlvalues(
                    self.person))

        if participations_filter:
            constraints.append('(' + ' OR '.join(participations_filter) + ')')

        return constraints
