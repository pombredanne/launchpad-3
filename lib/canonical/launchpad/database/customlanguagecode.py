# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database class for `ICustomLanguageCode`."""

__metaclass__ = type

__all__ = ['CustomLanguageCode']


from sqlobject import ForeignKey, StringCol
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ICustomLanguageCode


class CustomLanguageCode(SQLBase):
    """See `ICustomLanguageCode`."""

    implements(ICustomLanguageCode)

    _table = 'CustomLanguageCode'

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    language_code = StringCol(dbName='language_code', notNull=True)
    language = ForeignKey(
        dbName='language', foreignKey='Language', notNull=False, default=None)

