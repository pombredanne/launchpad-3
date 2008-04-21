# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""SQLBase implementation of IQuestionReopening."""

__metaclass__ = type

__all__ = ['QuestionReopening',
           'create_questionreopening']

from zope.event import notify
from zope.interface import implements
from zope.security.proxy import ProxyFactory

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import IQuestionReopening, QuestionStatus
from canonical.launchpad.validators.person import validate_public_person


class QuestionReopening(SQLBase):
    """A table recording each time a question is re-opened."""

    implements(IQuestionReopening)

    _table = 'QuestionReopening'

    question = ForeignKey(
        dbName='question', foreignKey='Question', notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    reopener = ForeignKey(
        dbName='reopener', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    answerer = ForeignKey(
        dbName='answerer', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)
    date_solved = UtcDateTimeCol(notNull=False, default=None)
    priorstate = EnumCol(schema=QuestionStatus, notNull=True)

# XXX flacoste 2006-10-25 The QuestionReopening is probably not that useful
# anymore since the question history is nearly completely tracked in the
# question message trails. (Only missing information is the previous recorded
# answer.) If we decide to still keep that class, this subscriber should
# probably be moved outside of database code.
def create_questionreopening(question, event):
    """Event subscriber that creates a QuestionReopening whenever a question
    with an answer changes back to the OPEN state.
    """
    if question.status != QuestionStatus.OPEN:
        return

    # Only create a QuestionReopening if the question had previsouly an
    # answer.
    old_question = event.object_before_modification
    if old_question.answerer is None:
        return
    assert question.answerer is None, (
        "Open question shouldn't have an answerer.")

    # The last added message is the cause of the reopening.
    reopen_msg = question.messages[-1]

    # Make sure that the last message is really the last added one.
    assert [reopen_msg] == (
        list(set(question.messages).difference(old_question.messages))), (
            "Reopening message isn't the last one.")

    reopening = QuestionReopening(
            question=question, reopener=reopen_msg.owner,
            datecreated=reopen_msg.datecreated,
            answerer=old_question.answerer,
            date_solved=old_question.date_solved,
            priorstate=old_question.status)

    reopening = ProxyFactory(reopening)
    notify(SQLObjectCreatedEvent(reopening, user=reopen_msg.owner))

