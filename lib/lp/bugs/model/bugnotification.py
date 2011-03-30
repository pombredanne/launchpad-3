# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Bug notifications."""

__metaclass__ = type
__all__ = [
    'BugNotification',
    'BugNotificationFilter',
    'BugNotificationRecipient',
    'BugNotificationSet',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    StringCol,
    )
from storm.expr import (
    In,
    Join,
    LeftJoin,
    )
from storm.store import Store
from storm.locals import (
    Int,
    Reference,
    )
from zope.interface import implements

from canonical.config import config
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.launchpad.database.message import Message
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.enum import BugNotificationStatus
from lp.bugs.interfaces.bugnotification import (
    IBugNotification,
    IBugNotificationFilter,
    IBugNotificationRecipient,
    IBugNotificationSet,
    )
from lp.bugs.model.bugactivity import BugActivity
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.structuralsubscription import StructuralSubscription
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.stormbase import StormBase


class BugNotification(SQLBase):
    """A textual representation about a bug change."""
    implements(IBugNotification)

    message = ForeignKey(dbName='message', notNull=True, foreignKey='Message')
    activity = ForeignKey(
        dbName='activity', notNull=False, foreignKey='BugActivity')
    bug = ForeignKey(dbName='bug', notNull=True, foreignKey='Bug')
    is_comment = BoolCol(notNull=True)
    date_emailed = UtcDateTimeCol(notNull=False)
    status = EnumCol(
        dbName='status',
        schema=BugNotificationStatus, default=BugNotificationStatus.PENDING,
        notNull=True)

    @property
    def recipients(self):
        """See `IBugNotification`."""
        return BugNotificationRecipient.selectBy(
            bug_notification=self, orderBy='id')

    @property
    def bug_filters(self):
        """See `IStructuralSubscription`."""
        return IStore(BugSubscriptionFilter).find(
            BugSubscriptionFilter,
            (BugSubscriptionFilter.id ==
             BugNotificationFilter.bug_subscription_filter_id),
            BugNotificationFilter.bug_notification == self)


class BugNotificationSet:
    """A set of bug notifications."""
    implements(IBugNotificationSet)

    def getNotificationsToSend(self):
        """See IBugNotificationSet."""
        # We preload the bug activity and the message in order to
        # try to reduce subsequent database calls: try to get direct
        # dependencies at once.  We could also get the person and the
        # bug, but we expect those to be shared, so we don't get them here
        # so we give Storm a better chance to cache.  We carefully look at
        # bugID and the ownerID here so as not to load the data
        # unnecessarily.
        store = IStore(BugNotification)
        source = store.using(BugNotification,
                             Join(Message,
                                  BugNotification.message==Message.id),
                             LeftJoin(
                                BugActivity,
                                BugNotification.activity==BugActivity.id))
        results = list(source.find(
            (BugNotification, BugActivity, Message),
            BugNotification.date_emailed == None).order_by(
            'BugNotification.bug', '-BugNotification.id'))
        interval = timedelta(
            minutes=int(config.malone.bugnotification_interval))
        time_limit = (
            datetime.now(pytz.timezone('UTC')) - interval)
        last_omitted_notification = None
        pending_notifications = []
        for notification, ignore, ignore in results:
            if notification.message.datecreated > time_limit:
                last_omitted_notification = notification
            elif (last_omitted_notification is not None and
                notification.message.ownerID ==
                   last_omitted_notification.message.ownerID and
                notification.bugID == last_omitted_notification.bugID and
                last_omitted_notification.message.datecreated -
                notification.message.datecreated < interval):
                last_omitted_notification = notification
            if last_omitted_notification != notification:
                last_omitted_notification = None
                pending_notifications.append(notification)
        pending_notifications.reverse()
        return pending_notifications

    def addNotification(self, bug, is_comment, message, recipients, activity):
        """See `IBugNotificationSet`."""
        if not recipients:
            return
        bug_notification = BugNotification(
            bug=bug, is_comment=is_comment,
            message=message, date_emailed=None, activity=activity)
        store = Store.of(bug_notification)
        # XXX jamesh 2008-05-21: these flushes are to fix ordering
        # problems in the bugnotification-sending.txt tests.
        store.flush()
        sql_values = []
        for recipient in recipients:
            reason_body, reason_header = recipients.getReason(recipient)
            sql_values.append('(%s, %s, %s, %s)' % sqlvalues(
                bug_notification, recipient, reason_header, reason_body))
        # We add all the recipients in a single SQL statement to make
        # this a bit more efficient for bugs with many subscribers.
        store.execute("""
            INSERT INTO BugNotificationRecipient
              (bug_notification, person, reason_header, reason_body)
            VALUES %s;""" % ', '.join(sql_values))
        return bug_notification

    def getFiltersByRecipient(self, notifications, recipient):
        """See `IBugNotificationSet`."""
        store = IStore(BugSubscriptionFilter)
        source = store.using(
            BugSubscriptionFilter,
            Join(BugNotificationFilter,
                 BugSubscriptionFilter.id ==
                    BugNotificationFilter.bug_subscription_filter_id),
            Join(StructuralSubscription,
                 BugSubscriptionFilter.structural_subscription_id ==
                    StructuralSubscription.id),
            Join(TeamParticipation,
                 TeamParticipation.teamID ==
                    StructuralSubscription.subscriberID))
        return source.find(
            BugSubscriptionFilter,
            In(BugNotificationFilter.bug_notification_id,
               [notification.id for notification in notifications]),
            TeamParticipation.personID == recipient.id)


class BugNotificationRecipient(SQLBase):
    """A recipient of a bug notification."""
    implements(IBugNotificationRecipient)

    bug_notification = ForeignKey(
        dbName='bug_notification', notNull=True, foreignKey='BugNotification')
    person = ForeignKey(
        dbName='person', notNull=True, foreignKey='Person')
    reason_header = StringCol(dbName='reason_header', notNull=True)
    reason_body = StringCol(dbName='reason_body', notNull=True)


class BugNotificationFilter(StormBase):
    """See `IBugNotificationFilter`."""
    implements(IBugNotificationFilter)

    __storm_table__ = "BugNotificationFilter"
    __storm_primary__ = "bug_notification_id", "bug_subscription_filter_id"

    def __init__(self, bug_notification, bug_subscription_filter):
        self.bug_notification = bug_notification
        self.bug_subscription_filter = bug_subscription_filter

    bug_notification_id = Int(
        "bug_notification", allow_none=False)
    bug_notification = Reference(
        bug_notification_id, "BugNotification.id")

    bug_subscription_filter_id = Int(
        "bug_subscription_filter", allow_none=False)
    bug_subscription_filter = Reference(
        bug_subscription_filter_id, "BugSubscriptionFilter.id")
