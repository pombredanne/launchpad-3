# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Person notifications."""

__metaclass__ = type
__all__ = [
    'PersonNotification',
    'PersonNotificationSet',
    ]

from sqlobject import ForeignKey, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces.personnotification import (
    IPersonNotification, IPersonNotificationSet)


class PersonNotification(SQLBase):
    """See `IPersonNotification`."""
    implements(IPersonNotification)

    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_emailed = UtcDateTimeCol(notNull=False)
    body = StringCol(notNull=True)
    subject = StringCol(notNull=True)


class PersonNotificationSet:
    """See `IPersonNotificationSet`."""
    implements(IPersonNotificationSet)

    def getNotificationsToSend(self):
        """See `IPersonNotificationSet`."""
        return PersonNotification.selectBy(
            date_emailed=None, orderBy=['date_created,id'])

    def addNotification(self, person, subject, body):
        """See `IPersonNotificationSet`."""
        return PersonNotification(person=person, subject=subject, body=body)

    def getNotificationsOlderThan(self, time_limit):
        """See `IPersonNotificationSet`."""
        return PersonNotification.select(
            'date_created < %s' % sqlvalues(time_limit))

