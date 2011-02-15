# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notifications."""

__metaclass__ = type

from datetime import datetime, timedelta
from itertools import chain
import unittest
import pytz

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from testtools.matchers import Not
from transaction import commit
from zope.component import getUtility
from zope.event import notify
from zope.interface import providedBy

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database.message import MessageSet
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.launchpad.ftests import login
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.adapters.bugchange import (
    BranchLinkedToBug,
    BranchUnlinkedFromBug,
    BugAttachmentChange,
    BugDuplicateChange,
    BugTagsChange,
    BugTaskStatusChange,
    BugTitleChange,
    BugVisibilityChange,
    BugWatchAdded,
    BugWatchRemoved,
    CveLinkedToBug,
    CveUnlinkedFromBug,
    )
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugnotification import IBugNotificationSet
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IUpstreamBugTask,
    )
from lp.bugs.model.bugnotification import (
    BugNotification,
    BugNotificationSet,
    )
from lp.bugs.scripts.bugnotification import get_email_notifications
from lp.services.propertycache import cachedproperty
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import lp_dbuser
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import Contains


class TestNotificationRecipientsOfPrivateBugs(unittest.TestCase):
    """Test who get notified of changes to private bugs."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        factory = LaunchpadObjectFactory()
        self.product_owner = factory.makePerson(name="product-owner")
        self.product = factory.makeProduct(owner=self.product_owner)
        self.product_subscriber = factory.makePerson(
            name="product-subscriber")
        self.product.addBugSubscription(
            self.product_subscriber, self.product_subscriber)
        self.bug_subscriber = factory.makePerson(name="bug-subscriber")
        self.bug_owner = factory.makePerson(name="bug-owner")
        self.private_bug = factory.makeBug(
            product=self.product, private=True, owner=self.bug_owner)
        self.reporter = self.private_bug.owner
        self.private_bug.subscribe(self.bug_subscriber, self.reporter)
        [self.product_bugtask] = self.private_bug.bugtasks
        self.direct_subscribers = set(
            person.name for person in [self.bug_subscriber, self.reporter])

    def test_status_change(self):
        # Status changes are sent to the direct subscribers only.
        bugtask_before_modification = Snapshot(
            self.product_bugtask, providing=providedBy(self.product_bugtask))
        self.product_bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.private_bug.owner)
        notify(ObjectModifiedEvent(
            self.product_bugtask, bugtask_before_modification, ['status'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(self.direct_subscribers, notified_people)

    def test_add_comment(self):
        # Comment additions are sent to the direct subscribers only.
        self.private_bug.newMessage(
            self.reporter, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(self.direct_subscribers, notified_people)

    def test_bug_edit(self):
        # Bug edits are sent to direct the subscribers only.
        bug_before_modification = Snapshot(
            self.private_bug, providing=providedBy(self.private_bug))
        self.private_bug.description = 'description'
        notify(ObjectModifiedEvent(
            self.private_bug, bug_before_modification, ['description'],
            user=self.reporter))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(self.direct_subscribers, notified_people)


class TestNotificationsSentForBugExpiration(TestCaseWithFactory):
    """Ensure that question subscribers are notified about bug expiration."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestNotificationsSentForBugExpiration, self).setUp(
            user='test@canonical.com')
        # We need a product, a bug for this product, a question linked
        # to the bug and a subscriber.
        self.product = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.product)
        question = self.factory.makeQuestion(target=self.product)
        self.subscriber = self.factory.makePerson()
        question.subscribe(self.subscriber)
        question.linkBug(self.bug)
        # Flush pending notifications for question creation.
        pop_notifications()
        self.layer.switchDbUser(config.malone.expiration_dbuser)

    def test_notifications_for_question_subscribers(self):
        # Ensure that notifications are sent to subscribers of a
        # question linked to the expired bug.
        bugtask = self.bug.default_bugtask
        bugtask_before_modification = Snapshot(
            bugtask, providing=IUpstreamBugTask)
        bugtask.transitionToStatus(BugTaskStatus.EXPIRED, self.product.owner)
        bug_modified = ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ["status"])
        notify(bug_modified)
        self.assertContentEqual(
            [self.product.owner.preferredemail.email,
             self.subscriber.preferredemail.email],
            [mail['To'] for mail in pop_notifications()])


class TestNotificationProcessingWithoutRecipients(TestCaseWithFactory):
    """Adding notificatons without any recipients does not cause any harm.

    In some cases, we may have attempts to send bug notifications for bugs
    that do not have any notification recipients.
    """

    layer = LaunchpadZopelessLayer

    def test_addNotification_without_recipients(self):
        # We can call BugNotificationSet.addNotification() with a empty
        # recipient list.
        #
        # No explicit assertion is necessary in this test -- we just want
        # to be sure that calling BugNotificationSet.addNotification()
        # does not lead to an exception caused by an SQL syntax error for
        # a command that ends with "VALUES ;"
        bug = self.factory.makeBug()
        message = MessageSet().fromText(
            subject='subject', content='content')
        BugNotificationSet().addNotification(
            bug=bug, is_comment=False, message=message, recipients=[],
            activity=None)


class TestNotificationsForDuplicates(TestCaseWithFactory):
    """Test who gets notified about actions on duplicate bugs."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestNotificationsForDuplicates, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.dupe_bug = self.factory.makeBug()
        self.dupe_bug.markAsDuplicate(self.bug)
        self.dupe_subscribers = set().union(
            self.dupe_bug.getDirectSubscribers(),
            self.dupe_bug.getIndirectSubscribers())

    def test_comment_notifications(self):
        # New comments are only sent to subscribers of the duplicate
        # bug, not to subscribers of the master bug.
        self.dupe_bug.newMessage(
            self.dupe_bug.owner, subject='subject', content='content')
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)

    def test_duplicate_edit_notifications(self):
        # Bug edits for a duplicate are sent to duplicate subscribers only.
        bug_before_modification = Snapshot(
            self.dupe_bug, providing=providedBy(self.dupe_bug))
        self.dupe_bug.description = 'A changed description'
        notify(ObjectModifiedEvent(
            self.dupe_bug, bug_before_modification, ['description'],
            user=self.dupe_bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)

    def test_branch_linked_notification(self):
        # Notices for branches linked to a duplicate are sent only
        # to subscribers of the duplicate.
        #
        # No one should really do this, but this case covers notices
        # provided by the Bug.addChange mechanism.
        branch = self.factory.makeBranch(owner=self.dupe_bug.owner)
        self.dupe_bug.linkBranch(branch, self.dupe_bug.owner)
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        recipients = set(
            recipient.person
            for recipient in latest_notification.recipients)
        self.assertEqual(self.dupe_subscribers, recipients)


class NotificationForRegistrantsMixin:
    """Mixin for testing when registrants get notified."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(NotificationForRegistrantsMixin, self).setUp(
            user='foo.bar@canonical.com')
        self.pillar_owner = self.factory.makePerson(name="distro-owner")
        self.bug_owner = self.factory.makePerson(name="bug-owner")
        self.pillar = self.makePillar()
        self.bug = self.makeBug()

    def test_notification_uses_malone(self):
        self.pillar.official_malone = True
        direct = self.bug.getDirectSubscribers()
        indirect = self.bug.getIndirectSubscribers()
        self.assertThat(direct, Not(Contains(self.pillar_owner)))
        self.assertThat(indirect, Contains(self.pillar_owner))

    def test_notification_does_not_use_malone(self):
        self.pillar.official_malone = False
        direct = self.bug.getDirectSubscribers()
        indirect = self.bug.getIndirectSubscribers()
        self.assertThat(direct, Not(Contains(self.pillar_owner)))
        self.assertThat(indirect, Not(Contains(self.pillar_owner)))

    def test_status_change_uses_malone(self):
        # Status changes are sent to the direct and indirect subscribers.
        self.pillar.official_malone = True
        [bugtask] = self.bug.bugtasks
        all_subscribers = set(
            [person.name for person in chain(
                    self.bug.getDirectSubscribers(),
                    self.bug.getIndirectSubscribers())])
        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.bug.owner)
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'],
            user=self.bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(all_subscribers, notified_people)
        self.assertThat(all_subscribers, Contains(self.pillar_owner.name))

    def test_status_change_does_not_use_malone(self):
        # Status changes are sent to the direct and indirect subscribers.
        self.pillar.official_malone = False
        [bugtask] = self.bug.bugtasks
        all_subscribers = set(
            [person.name for person in chain(
                    self.bug.getDirectSubscribers(),
                    self.bug.getIndirectSubscribers())])
        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(
            BugTaskStatus.INVALID, self.bug.owner)
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'],
            user=self.bug.owner))
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notified_people = set(
            recipient.person.name
            for recipient in latest_notification.recipients)
        self.assertEqual(all_subscribers, notified_people)
        self.assertThat(
            all_subscribers, Not(Contains(self.pillar_owner.name)))


class TestNotificationsForRegistrantsForDistros(
    NotificationForRegistrantsMixin, TestCaseWithFactory):
    """Test when distribution registrants get notified."""

    def makePillar(self):
        return self.factory.makeDistribution(
            owner=self.pillar_owner)

    def makeBug(self):
        return self.factory.makeBug(
            distribution=self.pillar,
            owner=self.bug_owner)


class TestNotificationsForRegistrantsForProducts(
    NotificationForRegistrantsMixin, TestCaseWithFactory):
    """Test when product registrants get notified."""

    def makePillar(self):
        return self.factory.makeProduct(
            owner=self.pillar_owner)

    def makeBug(self):
        return self.factory.makeBug(
            product=self.pillar,
            owner=self.bug_owner)


class EmailNotificationTestBase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(EmailNotificationTestBase, self).setUp()
        login('foo.bar@canonical.com')
        self.product_owner = self.factory.makePerson(name="product-owner")
        self.person = self.factory.makePerson(name="sample-person")
        self.product = self.factory.makeProduct(owner=self.product_owner)
        self.product_subscriber = self.factory.makePerson(
            name="product-subscriber")
        self.product.addBugSubscription(
            self.product_subscriber, self.product_subscriber)
        self.bug_subscriber = self.factory.makePerson(name="bug-subscriber")
        self.bug_owner = self.factory.makePerson(name="bug-owner")
        self.bug = self.factory.makeBug(
            product=self.product, private=False, owner=self.bug_owner)
        self.reporter = self.bug.owner
        self.bug.subscribe(self.bug_subscriber, self.reporter)
        [self.product_bugtask] = self.bug.bugtasks
        commit()
        login('test@canonical.com')
        self.layer.switchDbUser(config.malone.bugnotification_dbuser)
        self.now = datetime.now(pytz.timezone('UTC'))
        self.ten_minutes_ago = self.now - timedelta(minutes=10)
        self.notification_set = getUtility(IBugNotificationSet)
        for notification in self.notification_set.getNotificationsToSend():
            notification.date_emailed = self.now
        flush_database_updates()

    def tearDown(self):
        for notification in self.notification_set.getNotificationsToSend():
            notification.date_emailed = self.now
        flush_database_updates()
        super(EmailNotificationTestBase, self).tearDown()

    def get_messages(self):
        notifications = self.notification_set.getNotificationsToSend()
        email_notifications = get_email_notifications(notifications)
        for bug_notifications, messages in email_notifications:
            for message in messages:
                yield message, message.get_payload(decode=True)


class EmailNotificationsBugMixin:

    change_class = change_name = old = new = alt = unexpected_text = None

    def change(self, old, new):
        self.bug.addChange(
            self.change_class(
                self.ten_minutes_ago, self.person, self.change_name,
                old, new))

    def change_other(self):
        self.bug.addChange(
            BugVisibilityChange(
                self.ten_minutes_ago, self.person, "private",
                False, True))

    def test_change_seen(self):
        # A smoketest.
        self.change(self.old, self.new)
        message, body = self.get_messages().next()
        self.assertThat(body, Contains(self.unexpected_text))

    def test_undone_change_sends_no_emails(self):
        self.change(self.old, self.new)
        self.change(self.new, self.old)
        self.assertEqual(list(self.get_messages()), [])

    def test_undone_change_is_not_included(self):
        self.change(self.old, self.new)
        self.change(self.new, self.old)
        self.change_other()
        message, body = self.get_messages().next()
        self.assertThat(body, Not(Contains(self.unexpected_text)))

    def test_multiple_undone_changes_sends_no_emails(self):
        self.change(self.old, self.new)
        self.change(self.new, self.alt)
        self.change(self.alt, self.old)
        self.assertEqual(list(self.get_messages()), [])


class EmailNotificationsBugNotRequiredMixin(EmailNotificationsBugMixin):
    # This test collection is for attributes that can be None.

    def test_added_removed_sends_no_emails(self):
        self.change(None, self.old)
        self.change(self.old, None)
        self.assertEqual(list(self.get_messages()), [])

    def test_removed_added_sends_no_emails(self):
        self.change(self.old, None)
        self.change(None, self.old)
        self.assertEqual(list(self.get_messages()), [])

    def test_duplicate_marked_changed_removed_sends_no_emails(self):
        self.change(None, self.old)
        self.change(self.old, self.new)
        self.change(self.new, None)
        self.assertEqual(list(self.get_messages()), [])


class EmailNotificationsBugTaskMixin(EmailNotificationsBugMixin):

    def change(self, old, new, index=0):
        self.bug.addChange(
            self.change_class(
                self.bug.bugtasks[index], self.ten_minutes_ago,
                self.person, self.change_name, old, new))

    def test_changing_on_different_bugtasks_is_not_undoing(self):
        with lp_dbuser():
            product2 = self.factory.makeProduct(owner=self.product_owner)
            self.bug.addTask(self.product_owner, product2)
        self.change(self.old, self.new, index=0)
        self.change(self.new, self.old, index=1)
        message, body = self.get_messages().next()
        self.assertThat(body, Contains(self.unexpected_text))


class EmailNotificationsAddedRemovedMixin:

    old = new = added_message = removed_message = None
    def add(self, item):
        raise NotImplementedError
    remove = add

    def test_added_seen(self):
        self.add(self.old)
        message, body = self.get_messages().next()
        self.assertThat(body, Contains(self.added_message))

    def test_added_removed_sends_no_emails(self):
        self.add(self.old)
        self.remove(self.old)
        self.assertEqual(list(self.get_messages()), [])

    def test_removed_added_sends_no_emails(self):
        self.remove(self.old)
        self.add(self.old)
        self.assertEqual(list(self.get_messages()), [])
        
    def test_added_another_removed_sends_emails(self):
        self.add(self.old)
        self.remove(self.new)
        message, body = self.get_messages().next()
        self.assertThat(body, Contains(self.added_message))
        self.assertThat(body, Contains(self.removed_message))


class TestEmailNotificationsBugTitle(
    EmailNotificationsBugMixin, EmailNotificationTestBase):

    change_class = BugTitleChange
    change_name = "title"
    old = "Old summary"
    new = "New summary"
    alt = "Another summary"
    unexpected_text = '** Summary changed:'


class TestEmailNotificationsBugTags(
    EmailNotificationsBugMixin, EmailNotificationTestBase):

    change_class = BugTagsChange
    change_name = "tags"
    old = ['foo', 'bar', 'baz']
    new = ['foo', 'bar']
    alt = ['bing', 'shazam']
    unexpected_text = '** Tags'

    def test_undone_ordered_set_sends_no_email(self):
        # Tags use ordered sets to generate change descriptions, which we
        # demonstrate here.
        self.change(['foo', 'bar', 'baz'], ['foo', 'bar'])
        self.change(['foo', 'bar'], ['baz', 'bar', 'foo', 'bar'])
        self.assertEqual(list(self.get_messages()), [])


class TestEmailNotificationsBugDuplicate(
    EmailNotificationsBugNotRequiredMixin, EmailNotificationTestBase):

    change_class = BugDuplicateChange
    change_name = "duplicateof"
    unexpected_text = 'duplicate'

    def _bug(self):
        with lp_dbuser():
            return self.factory.makeBug()

    old = cachedproperty('old')(_bug)
    new = cachedproperty('new')(_bug)
    alt = cachedproperty('alt')(_bug)


class TestEmailNotificationsBugTaskStatus(
    EmailNotificationsBugTaskMixin, EmailNotificationTestBase):

    change_class = BugTaskStatusChange
    change_name = "status"
    old = BugTaskStatus.TRIAGED
    new = BugTaskStatus.INPROGRESS
    alt = BugTaskStatus.INVALID
    unexpected_text = 'Status: '


class TestEmailNotificationsBugWatch(
    EmailNotificationsAddedRemovedMixin, EmailNotificationTestBase):

    # Note that this is for bugwatches added to bugs.  Bugwatches added
    # to bugtasks are separate animals AIUI, and we don't try to combine
    # them here for notifications.  Bugtasks have only zero or one
    # bugwatch, so they can be handled just as a simple bugtask attribute
    # change, like status.

    added_message = '** Bug watch added:'
    removed_message = '** Bug watch removed:'

    @cachedproperty
    def tracker(self):
        with lp_dbuser():
            return self.factory.makeBugTracker()

    def _watch(self, identifier='123'):
        with lp_dbuser():
            # This actually creates a notification all by itself.  However,
            # it won't be sent out for another five minutes.  Therefore,
            # we send out separate change notifications.
            return self.bug.addWatch(
                self.tracker, identifier, self.product_owner)

    old = cachedproperty('old')(_watch)
    new = cachedproperty('new')(lambda self: self._watch('456'))

    def add(self, item):
        with lp_dbuser():
            self.bug.addChange(
                BugWatchAdded(
                    self.ten_minutes_ago, self.product_owner, item))

    def remove(self, item):
        with lp_dbuser():
            self.bug.addChange(
                BugWatchRemoved(
                    self.ten_minutes_ago, self.product_owner, item))


class TestEmailNotificationsBranch(
    EmailNotificationsAddedRemovedMixin, EmailNotificationTestBase):

    added_message = '** Branch linked:'
    removed_message = '** Branch unlinked:'

    def _branch(self):
        with lp_dbuser():
            return self.factory.makeBranch()

    old = cachedproperty('old')(_branch)
    new = cachedproperty('new')(_branch)

    def add(self, item):
        with lp_dbuser():
            self.bug.addChange(
                BranchLinkedToBug(
                    self.ten_minutes_ago, self.person, item, self.bug))

    def remove(self, item):
        with lp_dbuser():
            self.bug.addChange(
                BranchUnlinkedFromBug(
                    self.ten_minutes_ago, self.person, item, self.bug))


class TestEmailNotificationsCVE(
    EmailNotificationsAddedRemovedMixin, EmailNotificationTestBase):

    added_message = '** CVE added:'
    removed_message = '** CVE removed:'

    def _cve(self, sequence):
        with lp_dbuser():
            return self.factory.makeCVE(sequence)

    old = cachedproperty('old')(lambda self: self._cve('2020-1234'))
    new = cachedproperty('new')(lambda self: self._cve('2020-5678'))

    def add(self, item):
        with lp_dbuser():
            self.bug.addChange(
                CveLinkedToBug(
                    self.ten_minutes_ago, self.person, item))

    def remove(self, item):
        with lp_dbuser():
            self.bug.addChange(
                CveUnlinkedFromBug(
                    self.ten_minutes_ago, self.person, item))

# I believe attachment change notifications are broken.  I'll be writing a
# test to prove it in another branch.

#     def test_attachment_added_removed_sends_no_emails(self):
#     def test_attachment_removed_added_sends_no_emails(self):
#     def test_attachment_added_another_removed_sends_emails(self):

#  XXX This also still needs to be dealt with properly.
#     def test_unsent_email_marks_notifications_properly(self):
#         self.bug.addChange(
#             BugTitleChange(
#                 self.ten_minutes_ago, self.person, "title",
#                 "Old summary", "New summary"))
#         self.bug.addChange(
#             BugTitleChange(
#                 self.ten_minutes_ago, self.person, "title",
#                 "New summary", "Old summary"))
#         discarded = list(self.get_messages())
#         # This makes sure we have cleaned out the unsent messages.
#         self.assertEqual(
#             list(self.notification_set.getNotificationsToSend()), [])
