# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['RevisionNumber']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IRevisionNumber


class RevisionNumber(SQLBase):
    """The association between a revision and a branch."""

    implements(IRevisionNumber)

    _table = 'RevisionNumber'
    
    rev_no = IntCol(notNull=True)
    branch = ForeignKey(
        dbName='branch', foreignKey='Branch', notNull=True)
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)
