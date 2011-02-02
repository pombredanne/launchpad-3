# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from storm.store import Store

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.bugs.adapters.bugdelta import BugDelta
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bugtask import BugTaskDelta
from lp.bugs.model.bugnotification import (
    BugNotification,
    BugNotificationRecipient,
    )
from lp.bugs.subscribers.bug import add_bug_change_notifications
from lp.registry.enum import BugNotificationLevel
from lp.registry.model.person import Person
from lp.testing import TestCaseWithFactory


class BugSubscriberTestCase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(BugSubscriberTestCase, self).setUp()
        self.bug = self.factory.makeBug()
        self.bugtask = self.bug.default_bugtask
        self.user = self.factory.makePerson()
        self.lifecycle_subscriber = self.newSubscriber(
            self.bug, 'lifecycle-subscriber', BugNotificationLevel.LIFECYCLE)
        self.metadata_subscriber = self.newSubscriber(
            self.bug, 'metadata-subscriber', BugNotificationLevel.METADATA)
        self.old_persons = set(self.getNotifiedPersons(include_all=True))

    def createDelta(self, user=None, **kwargs):
        if user is None:
            user = self.user
        return BugDelta(
            bug=self.bug,
            bugurl=canonical_url(self.bug),
            user=user,
            **kwargs)

    def newSubscriber(self, bug, name, level):
        # Create a new bug subscription with a new person.
        subscriber = self.factory.makePerson(name=name)
        subscription = bug.subscribe(subscriber, subscriber,
                                     level=level)
        return subscriber

    def getNotifiedPersons(self, include_all=False):
        notified_persons = Store.of(self.bug).find(
            Person,
            BugNotification.id==BugNotificationRecipient.bug_notificationID,
            BugNotificationRecipient.personID==Person.id,
            BugNotification.bugID==self.bug.id)
        if include_all:
            return list(notified_persons)
        else:
            return set(notified_persons) - self.old_persons

    def test_add_bug_change_notifications_metadata(self):
        # Changing a bug description is considered to have change_level
        # of BugNotificationLevel.METADATA.
        bug_delta = self.createDelta(
            description={'new': 'new description',
                         'old': self.bug.description})

        add_bug_change_notifications(bug_delta)

        self.assertContentEqual([self.metadata_subscriber],
                                self.getNotifiedPersons())

    def test_add_bug_change_notifications_lifecycle(self):
        # Changing a bug description is considered to have change_level
        # of BugNotificationLevel.LIFECYCLE.
        bugtask_delta = BugTaskDelta(
            bugtask=self.bugtask,
            status={'old': BugTaskStatus.NEW,
                    'new': BugTaskStatus.FIXRELEASED})
        bug_delta = self.createDelta(
            bugtask_deltas=bugtask_delta)

        add_bug_change_notifications(bug_delta)

        # Both a LIFECYCLE and METADATA subscribers get notified.
        self.assertContentEqual([self.metadata_subscriber,
                                 self.lifecycle_subscriber],
                                self.getNotifiedPersons())

    def test_add_bug_change_notifications_duplicate_lifecycle(self):
        # Marking a bug as a duplicate of a resolved bug is
        # a lifecycle change.
        duplicate_of = self.factory.makeBug()
        duplicate_of.default_bugtask.transitionToStatus(
            BugTaskStatus.FIXRELEASED, self.user)
        bug_delta = self.createDelta(
            user=self.bug.owner,
            duplicateof={'old': None,
                         'new': duplicate_of})

        add_bug_change_notifications(bug_delta)

        # Both a LIFECYCLE and METADATA subscribers get notified.
        self.assertContentEqual([self.metadata_subscriber,
                                 self.lifecycle_subscriber],
                                self.getNotifiedPersons())

    def test_add_bug_change_notifications_duplicate_metadata(self):
        # Marking a bug as a duplicate of a unresolved bug is
        # a lifecycle change.
        duplicate_of = self.factory.makeBug()
        duplicate_of.default_bugtask.transitionToStatus(
            BugTaskStatus.INPROGRESS, self.user)
        bug_delta = self.createDelta(
            user=self.bug.owner,
            duplicateof={'old': None,
                         'new': duplicate_of})

        add_bug_change_notifications(bug_delta)

        # Only METADATA subscribers get notified.
        self.assertContentEqual([self.metadata_subscriber],
                                self.getNotifiedPersons())
