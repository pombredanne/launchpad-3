# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Revision', 'RevisionAuthor', 'RevisionParent', 'RevisionSet']

from zope.interface import implements
from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    IRevision, IRevisionAuthor, IRevisionParent, IRevisionSet)
from canonical.launchpad.helpers import shortlist


class Revision(SQLBase):
    """See IRevision."""

    implements(IRevision)

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    log_body = StringCol(notNull=True)
    gpgkey = ForeignKey(dbName='gpgkey', foreignKey='GPGKey', default=None)

    revision_author = ForeignKey(
        dbName='revision_author', foreignKey='RevisionAuthor', notNull=True)
    revision_id = StringCol(notNull=True, alternateID=True,
                            alternateMethodName='byRevisionID')
    revision_date = UtcDateTimeCol(notNull=False)

    @property
    def parents(self):
        """See IRevision.parents"""
        return shortlist(RevisionParent.selectBy(
            revision=self, orderBy='sequence'))

    @property
    def parent_ids(self):
        """Sequence of globally unique ids for the parents of this revision.

        The corresponding Revision objects can be retrieved, if they are
        present in the database, using the RevisionSet Zope utility.
        """
        return [parent.parent_id for parent in self.parents]


class RevisionAuthor(SQLBase):
    implements(IRevisionAuthor)

    _table = 'RevisionAuthor'

    name = StringCol(notNull=True, alternateID=True)


class RevisionParent(SQLBase):
    """The association between a revision and its parent."""

    implements(IRevisionParent)

    _table = 'RevisionParent'

    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)

    sequence = IntCol(notNull=True)
    parent_id = StringCol(notNull=True)


class RevisionSet:

    implements(IRevisionSet)

    def getByRevisionId(self, revision_id):
        return Revision.selectOneBy(revision_id=revision_id)

    def new(self, revision_id, log_body, revision_date, revision_author, owner,
            parent_ids):
        """See IRevisionSet.new()"""
        # create a RevisionAuthor if necessary:
        try:
            author = RevisionAuthor.byName(revision_author)
        except SQLObjectNotFound:
            author = RevisionAuthor(name=revision_author)

        revision = Revision(revision_id=revision_id,
                            log_body=log_body,
                            revision_date=revision_date,
                            revision_author=author,
                            owner=owner)
        seen_parents = set()
        for sequence, parent_id in enumerate(parent_ids):
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)
            RevisionParent(revision=revision, sequence=sequence,
                           parent_id=parent_id)
        
        return revision
