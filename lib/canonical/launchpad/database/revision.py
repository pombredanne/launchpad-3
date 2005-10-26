# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Revision', 'RevisionAuthor', 'RevisionParent', 'RevisionNumber']

from zope.interface import implements
from sqlobject import ForeignKey, IntCol, StringCol

from canonical.launchpad.interfaces import (
    IRevision, IRevisionAuthor, IRevisionParent, IRevisionNumber)

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol


class Revision(SQLBase):
    """See IRevision."""

    implements(IRevision)

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    log_body = StringCol(notNull=True)
    revision_author = ForeignKey(
        dbName='revision_author', foreignKey='RevisionAuthor', notNull=True)
    gpgkey = ForeignKey(dbName='gpgkey', foreignKey='GPGKey', default=None)
    revision_id = StringCol(notNull=True)
    revision_date = UtcDateTimeCol(notNull=False)

    @property
    def parent_ids(self):
        parents = RevisionParent.selectBy(revisionID=self, orderBy='sequence')
        return [parent.parent_id for parent in parents]


class RevisionAuthor(SQLBase):
    implements(IRevisionAuthor)

    _table = 'RevisionAuthor'

    name = StringCol(notNull=True)


class RevisionParent(SQLBase):
    """The association between a revision and its parent."""

    implements(IRevisionParent)

    _table = 'RevisionParent'

    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)
    sequence = IntCol(notNull=True)
    parent_id = StringCol(notNull=True)


class RevisionNumber(SQLBase):
    """The association between a revision and a branch."""

    implements(IRevisionNumber)

    _table = 'RevisionNumber'
    
    sequence = IntCol(notNull=True)
    branch = ForeignKey(
        dbName='branch', foreignKey='Branch', notNull=True)
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)
