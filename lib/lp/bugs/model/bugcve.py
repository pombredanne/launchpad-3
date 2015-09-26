# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BugCve']

from sqlobject import ForeignKey

from lp.services.database.sqlbase import SQLBase


class BugCve(SQLBase):
    """A table linking bugs and CVE entries."""

    _table = 'BugCve'

    # db field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    cve = ForeignKey(dbName='cve', foreignKey='Cve', notNull=True)
