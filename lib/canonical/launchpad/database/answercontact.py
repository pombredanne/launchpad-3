# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SupportContact']


from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IAnswerContact


class SupportContact(SQLBase):
    """An entry for an answer contact for an IQuestionTarget."""

    implements(IAnswerContact)

    _defaultOrder = ['id']

    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    product = ForeignKey(dbName='product', notNull=False, foreignKey='Product')
    distribution = ForeignKey(
        dbName='distribution', notNull=False, foreignKey='Distribution')
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', notNull=False,
        foreignKey='SourcePackageName')
