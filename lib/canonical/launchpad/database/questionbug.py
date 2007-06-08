# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""SQLBase implementation of IQuestionBug."""

__metaclass__ = type

__all__ = ['QuestionBug']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IQuestionBug

from canonical.database.sqlbase import SQLBase


class QuestionBug(SQLBase):
    """A link between a question and a bug."""

    implements(IQuestionBug)

    _table = 'QuestionBug'

    question = ForeignKey(
        dbName='question', foreignKey='Question', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)

    @property
    def target(self):
        """See IBugLink."""
        return self.question

