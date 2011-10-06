# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['CveReference']

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.bugs.interfaces.cvereference import ICveReference


class CveReference(SQLBase):
    """A CVE reference to some other tracking system."""

    implements(ICveReference)

    _table = 'CveReference'

    # db field names
    cve = ForeignKey(dbName='cve', foreignKey='Cve', notNull=True)
    source = StringCol(notNull=True)
    content = StringCol(notNull=True)
    url = StringCol(notNull=False, default=None)


