# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database classes related to bug nomination.

A bug nomination is a suggestion from a user that a bug be fixed in a
particular distro release or product series. A bug may have zero, one,
or more nominations.
"""

__metaclass__ = type
__all__ = ['BugNomination']

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IBugNomination, IBugTaskSet
from canonical.lp import dbschema

class BugNomination(SQLBase):
    implements(IBugNomination)
    _table = "BugNomination"

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    distrorelease = ForeignKey(
        dbName='distrorelease', foreignKey='DistroRelease',
        notNull=False, default=None)
    productseries = ForeignKey(
        dbName='productseries', foreignKey='ProductSeries',
        notNull=False, default=None)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    status = dbschema.EnumCol(
        dbName='status', notNull=True, schema=dbschema.BugNominationStatus,
        default=dbschema.BugNominationStatus.PENDING)

    @property
    def target(self):
        """See IBugNomination."""
        return self.distrorelease or self.productseries

    def approve(self, approver):
        """See IBugNomination."""
        self.status = dbschema.BugNominationStatus.APPROVED
        context = {}
        if self.distrorelease:
            context['distrorelease'] = self.distrorelease
        else:
            context['productseries'] = self.productseries
        getUtility(IBugTaskSet).createTask(
            bug=self.bug, owner=approver, **context)

    def decline(self, decliner):
        """See IBugNomination."""
        pass
