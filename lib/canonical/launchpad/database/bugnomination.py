# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database classes related to bug nomination.

A bug nomination is a suggestion from a user that a bug be fixed in a
particular distro release or product series. A bug may have zero, one,
or more nominations.
"""

__metaclass__ = type
__all__ = ['BugNomination']

from datetime import datetime

import pytz

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
    decider = ForeignKey(
        dbName='decider', foreignKey='Person', notNull=False, default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    datedecided = UtcDateTimeCol(notNull=False, default=None)
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
        self.decider = approver
        self.datedecided = datetime.now(pytz.timezone('UTC'))

        bugtaskset = getUtility(IBugTaskSet)
        if self.distrorelease:
            # Figure out which packages are affected in this distro for
            # this bug.
            targets = []
            distribution = self.distrorelease.distribution
            distrorelease = self.distrorelease
            for task in self.bug.bugtasks:
                if not task.distribution == distribution:
                    continue
                if task.sourcepackagename:
                    bugtaskset.createTask(
                        bug=self.bug, owner=approver,
                        distrorelease=distrorelease,
                        sourcepackagename=task.sourcepackagename)
                else:
                    bugtaskset.createTask(
                        bug=self.bug, owner=approver,
                        distrorelease=distrorelease)
        else:
            bugtaskset.createTask(
                bug=self.bug, owner=approver, productseries=self.productseries)

    def decline(self, decliner):
        """See IBugNomination."""
        self.status = dbschema.BugNominationStatus.DECLINED
        self.decider = decliner
        self.datedecided = datetime.now(pytz.timezone('UTC'))
