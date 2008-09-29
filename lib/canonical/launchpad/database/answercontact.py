# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""SQLBase implementation of  IAnswerContact."""

__metaclass__ = type
__all__ = ['AnswerContact']


from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IAnswerContact
from canonical.launchpad.validators.person import validate_public_person


class AnswerContact(SQLBase):
    """An entry for an answer contact for an `IQuestionTarget`."""

    implements(IAnswerContact)

    _defaultOrder = ['id']
    _table = 'AnswerContact'

    person = ForeignKey(
        dbName='person', notNull=True, foreignKey='Person',
        storm_validator=validate_public_person)
    product = ForeignKey(
        dbName='product', notNull=False, foreignKey='Product')
    distribution = ForeignKey(
        dbName='distribution', notNull=False, foreignKey='Distribution')
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', notNull=False,
        foreignKey='SourcePackageName')
