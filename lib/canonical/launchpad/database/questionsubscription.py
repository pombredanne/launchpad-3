# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""SQLBase implementation of IQuestionSubscription."""

__metaclass__ = type

__all__ = ['QuestionSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IQuestionSubscription

from canonical.database.sqlbase import SQLBase


class QuestionSubscription(SQLBase):
    """A subscription for person to a question."""

    implements(IQuestionSubscription)

    _table = 'QuestionSubscription'

    question = ForeignKey(
        dbName='question', foreignKey='Question', notNull=True)

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


