# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['AnswerContact']


from zope.interface import implements

from sqlobject import BoolCol, ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IAnswerContact


class AnswerContact(SQLBase):
    """An entry for an answer contact for an IQuestionTarget."""

    implements(IAnswerContact)

    _defaultOrder = ['id']
    _table = 'AnswerContact'

    person = ForeignKey(
        dbName='person', notNull=True, foreignKey='Person')
    product = ForeignKey(
        dbName='product', notNull=False, foreignKey='Product')
    distribution = ForeignKey(
        dbName='distribution', notNull=False, foreignKey='Distribution')
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', notNull=False,
        foreignKey='SourcePackageName')
    limited_languages = BoolCol(
        dbName='limited_languages', notNull=True, default=False)
