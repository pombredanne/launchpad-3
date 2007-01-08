# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POSelection']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IPOSelection


class POSelection(SQLBase):
    implements(IPOSelection)

    _table = 'POSelection'

    pomsgset = ForeignKey(foreignKey='POMsgSet', dbName='pomsgset',
        notNull=True)
    pluralform = IntCol(dbName='pluralform', notNull=True)
    activesubmission = ForeignKey(foreignKey='POSubmission',
        dbName='activesubmission', notNull=False, default=None)
    publishedsubmission = ForeignKey(foreignKey='POSubmission',
        dbName='publishedsubmission', notNull=False, default=None)
    reviewer = ForeignKey(foreignKey='Person', dbName='reviewer',
        notNull=False, default=None)
    date_reviewed = UtcDateTimeCol(dbName='date_reviewed', notNull=False,
        default=None)

    def isNewerThan(self, timestamp):
        """See IPOSelection."""
        if (self.activesubmission is not None and
            self.date_reviewed > timestamp):
            return True
        return False
