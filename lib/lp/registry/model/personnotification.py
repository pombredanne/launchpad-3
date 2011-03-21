# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Person notifications."""

__metaclass__ = type
__all__ = [
    'PersonNotification',
    'PersonNotificationSet',
    ]

from datetime import datetime

import pytz
from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.registry.interfaces.personnotification import (
    IPersonNotification,
    IPersonNotificationSet,
    )
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )


class PersonNotification(SQLBase):
    """See `IPersonNotification`."""
    implements(IPersonNotification)

    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_emailed = UtcDateTimeCol(notNull=False)
    body = StringCol(notNull=True)
    subject = StringCol(notNull=True)

    def send(self):
        """See `IPersonNotification`."""
        assert self.person.preferredemail is not None, (
            "Can't send a notification to a person without an email.")
        from_addr = config.canonical.bounce_address
        to_addr = format_address(
            self.person.displayname, self.person.preferredemail.email)
        simple_sendmail(from_addr, to_addr, self.subject, self.body)
        self.date_emailed = datetime.now(pytz.timezone('UTC'))


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

