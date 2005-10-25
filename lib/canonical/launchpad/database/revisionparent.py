# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['RevisionParent']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IRevisionParent


class RevisionParent(SQLBase):
    """The association between a revision and its parent."""

    implements(IRevisionParent)

    _table = 'RevisionParent'
    
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)
    parent = ForeignKey(
        dbName='parent', foreignKey='Revision', notNull=True)

