# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""SQLBase implementation of IQuestionSubscription."""

__metaclass__ = type

__all__ = ['QuestionSubscription']

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.answers.interfaces.questionsubscription import IQuestionSubscription
from lp.registry.interfaces.person import validate_public_person


class QuestionSubscription(SQLBase):
    """A subscription for person to a question."""

    implements(IQuestionSubscription)

    _table = 'QuestionSubscription'

    question = ForeignKey(
        dbName='question', foreignKey='Question', notNull=True)

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
