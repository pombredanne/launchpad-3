# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['CodeReviewSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ICodeReviewSubscription,
    )


class CodeReviewSubscription(SQLBase):
    """A table linking branch merge proposals and subscribers."""

    implements(ICodeReviewSubscription)

    _table = 'CodeReviewSubscription'

    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)
    date_created = UtcDateTimeCol(default=DEFAULT)
