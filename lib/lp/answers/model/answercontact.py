# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""SQLBase implementation of  IAnswerContact."""

__metaclass__ = type
__all__ = ['AnswerContact']


from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.answers.interfaces.answercontact import IAnswerContact
from lp.registry.interfaces.person import validate_public_person


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
