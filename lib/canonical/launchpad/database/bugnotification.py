# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Bug notifications."""

__metaclass__ = type
__all__ = [
    'BugNotification',
    'BugNotificationRecipient',
    'BugNotificationSet',
    ]

import pytz
from datetime import datetime, timedelta

from sqlobject import ForeignKey, BoolCol, StringCol
from storm.store import Store

from zope.interface import implements

from canonical.config import config
from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import (
    IBugNotification, IBugNotificationRecipient, IBugNotificationSet)


class BugNotification(SQLBase):
    """A textual representation about a bug change."""
    implements(IBugNotification)

    message = ForeignKey(dbName='message', notNull=True, foreignKey='Message')
    bug = ForeignKey(dbName='bug', notNull=True, foreignKey='Bug')
    is_comment = BoolCol(notNull=True)
    date_emailed = UtcDateTimeCol(notNull=False)

    @property
    def recipients(self):
        """See `IBugNotification`."""
        return BugNotificationRecipient.selectBy(
            bug_notification=self, orderBy='id')


class BugNotificationSet:
    """A set of bug notifications."""
    implements(IBugNotificationSet)

    def getNotificationsToSend(self):
        """See IBugNotificationSet."""
        notifications = BugNotification.select(
            """date_emailed IS NULL""", orderBy=['bug', '-id'])
        pending_notifications = list(notifications)
        omitted_notifications = []
        interval = timedelta(
            minutes=int(config.malone.bugnotification_interval))
        time_limit = (
            datetime.now(pytz.timezone('UTC')) - interval)

        last_omitted_notification = None
        for notification in pending_notifications:
            if notification.message.datecreated > time_limit:
                omitted_notifications.append(notification)
                last_omitted_notification = notification
            elif last_omitted_notification is not None:
                if (notification.message.owner ==
                       last_omitted_notification.message.owner and
                    notification.bug == last_omitted_notification.bug and
                    last_omitted_notification.message.datecreated -
                    notification.message.datecreated < interval):
                    omitted_notifications.append(notification)
                    last_omitted_notification = notification
            if last_omitted_notification != notification:
                last_omitted_notification = None

        pending_notifications = [
            notification
            for notification in pending_notifications
            if notification not in omitted_notifications
            ]
        pending_notifications.reverse()
        return pending_notifications

    def addNotification(self, bug, is_comment, message, recipients):
        """See `IBugNotificationSet`."""
        bug_notification = BugNotification(
            bug=bug, is_comment=is_comment,
            message=message, date_emailed=None)
        store = Store.of(bug_notification)
        # XXX jamesh 2008-05-21: these flushes are to fix ordering
        # problems in the bugnotification-sending.txt tests.
        store.flush()
        for recipient in recipients:
            reason_body, reason_header = recipients.getReason(recipient)
            BugNotificationRecipient(
                bug_notification=bug_notification, person=recipient,
                reason_header=reason_header, reason_body=reason_body)
            store.flush()
        return bug_notification


class BugNotificationRecipient(SQLBase):
    """A recipient of a bug notification."""
    implements(IBugNotificationRecipient)

    bug_notification = ForeignKey(
        dbName='bug_notification', notNull=True, foreignKey='BugNotification')
    person = ForeignKey(
        dbName='person', notNull=True, foreignKey='Person')
    reason_header = StringCol(dbName='reason_header', notNull=True)
    reason_body = StringCol(dbName='reason_body', notNull=True)
