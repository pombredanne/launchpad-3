# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'MentoringOffer',
    'MentorshipManager',
    ]

from zope.interface import implements

from sqlobject import (
    ForeignKey, SQLMultipleJoin, SQLRelatedJoin)

from canonical.launchpad.interfaces import (
    IMentoringOffer,
    IMentorshipManager,
    )

from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol


class MentoringOffer(SQLBase):
    """See IMentoringOffer."""

    implements(IMentoringOffer)

    _defaultOrder = ['bug', 'id']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    team = ForeignKey(dbName='team', notNull=True, foreignKey='Person')
    bug = ForeignKey(dbName='bug', notNull=False,
                     foreignKey='Bug', default=None)
    specification = ForeignKey(dbName='specification', notNull=False,
                     foreignKey='Specification', default=None)

    # attributes
    @property
    def target(self):
        """See IMentoringOffer."""
        if self.bug:
            return self.bug
        return self.specification


class MentorshipManager:
    """See IMentorshipManager."""

    implements(IMentorshipManager)

    displayname = 'the Mentorship Manager'
    title = 'Mentorship Manager'

    @property
    def mentoring_offers(self):
        return MentoringOffer.select()

