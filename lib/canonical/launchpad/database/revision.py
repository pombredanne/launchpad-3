# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Revision', 'RevisionAuthor']

from zope.interface import implements
from sqlobject import ForeignKey, IntCol, StringCol

from canonical.launchpad.interfaces import IRevision, IRevisionAuthor

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
        dbName='revision_author', foreignKey='RevisionAuthor', default=None)
    gpgkey = ForeignKey(dbName='gpgkey', foreignKey='GPGKey', default=None)
    revision_id = StringCol(notNull=True)
    revision_date = UtcDateTimeCol(notNull=False)
    committed_against = ForeignKey(
        dbName='committed_against', foreignKey='Revision', default=None)
    diff_adds = IntCol()
    diff_deletes = IntCol()

    # TODO: parents property -- DavidAllouche 2005-10-25


class RevisionAuthor(SQLBase):
    implements(IRevisionAuthor)

    _table = 'RevisionAuthor'

    name = StringCol(notNull=True)

