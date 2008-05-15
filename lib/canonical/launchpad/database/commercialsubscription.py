# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for a CommercialSubscription."""

__metaclass__ = type
__all__ = ['CommercialSubscription']

import datetime
import pytz

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol)

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ICommercialSubscription
from canonical.launchpad.validators.person import public_person_validator


class CommercialSubscription(SQLBase):
    implements(ICommercialSubscription)

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_last_modified = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_starts = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_expires = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', default=None,
        validator=public_person_validator)
    purchaser = ForeignKey(
        dbName='purchaser', foreignKey='Person', default=None,
        validator=public_person_validator)
    sales_system_id = StringCol(notNull=True)
    whiteboard = StringCol(default=None)

    @property
    def is_active(self):
        now = datetime.datetime.now(pytz.timezone('UTC'))
        return self.date_starts < now < self.date_expires
