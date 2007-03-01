# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'QuestionMessage',
    ]

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad import _

from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol

from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.interfaces import IMessage, IQuestionMessage

from canonical.lp import decorates
from canonical.lp.dbschema import QuestionAction, QuestionStatus


class QuestionMessage(SQLBase):
    """A table linking questions and messages."""

    implements(IQuestionMessage)

    decorates(IMessage, context='message')

    _table = 'QuestionMessage'

    question = ForeignKey(
        dbName='question', foreignKey='Question', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)

    action = EnumCol(
        schema=QuestionAction, notNull=True, default=QuestionAction.COMMENT)

    new_status = EnumCol(
        schema=QuestionStatus, notNull=True, default=QuestionStatus.OPEN)
