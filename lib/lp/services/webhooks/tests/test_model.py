# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lazr.lifecycle.event import ObjectModifiedEvent
from storm.store import Store
from testtools.matchers import (
    Equals,
    GreaterThan,
    HasLength,
    )
import transaction
from zope.component import getUtility
from zope.event import notify
from zope.security.checker import getChecker

from lp.services.database.interfaces import IStore
from lp.services.webapp.authorization import check_permission
from lp.services.webhooks.interfaces import (
    IWebhook,
    IWebhookSet,
    )
from lp.services.webhooks.model import WebhookJob
from lp.testing import (
    admin_logged_in,
    anonymous_logged_in,
    ExpectedException,
    login_person,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestWebhook(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_modifiedevent_sets_date_last_modified(self):
        # When a Webhook receives an object modified event, the last modified
        # date is set to UTC_NOW.
        webhook = self.factory.makeWebhook()
        transaction.commit()
        with admin_logged_in():
            old_mtime = webhook.date_last_modified
        notify(ObjectModifiedEvent(
            webhook, webhook, [IWebhook["delivery_url"]]))
        with admin_logged_in():
            self.assertThat(
                webhook.date_last_modified,
                GreaterThan(old_mtime))

    def test_event_types(self):
        # Webhook.event_types is a list of event type strings.
        webhook = self.factory.makeWebhook()
        with admin_logged_in():
            self.assertContentEqual([], webhook.event_types)
            webhook.event_types = ['foo', 'bar']
            self.assertContentEqual(['foo', 'bar'], webhook.event_types)

    def test_event_types_bad_structure(self):
        # It's not possible to set Webhook.event_types to a list of the
        # wrong type.
        webhook = self.factory.makeWebhook()
        with admin_logged_in():
            self.assertContentEqual([], webhook.event_types)
            with ExpectedException(AssertionError, '.*'):
                webhook.event_types = ['foo', [1]]
            self.assertContentEqual([], webhook.event_types)


class TestWebhookPermissions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_target_owner_can_view(self):
        target = self.factory.makeGitRepository()
        webhook = self.factory.makeWebhook(target=target)
        with person_logged_in(target.owner):
            self.assertTrue(check_permission('launchpad.View', webhook))

    def test_random_cannot_view(self):
        webhook = self.factory.makeWebhook()
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission('launchpad.View', webhook))

    def test_anonymous_cannot_view(self):
        webhook = self.factory.makeWebhook()
        with anonymous_logged_in():
            self.assertFalse(check_permission('launchpad.View', webhook))

    def test_get_permissions(self):
        expected_get_permissions = {
            'launchpad.View': set((
                'active', 'date_created', 'date_last_modified', 'deliveries',
                'delivery_url', 'destroySelf', 'event_types', 'getDelivery',
                'id', 'ping', 'registrant', 'registrant_id', 'secret',
                'setSecret', 'target')),
            }
        webhook = self.factory.makeWebhook()
        checker = getChecker(webhook)
        self.checkPermissions(
            expected_get_permissions, checker.get_permissions, 'get')

    def test_set_permissions(self):
        expected_set_permissions = {
            'launchpad.View': set((
                'active', 'delivery_url', 'event_types', 'registrant_id',
                'secret')),
            }
        webhook = self.factory.makeWebhook()
        checker = getChecker(webhook)
        self.checkPermissions(
            expected_set_permissions, checker.set_permissions, 'set')


class TestWebhookSetBase:

    layer = DatabaseFunctionalLayer

    def test_new(self):
        target = self.makeTarget()
        login_person(target.owner)
        person = self.factory.makePerson()
        hook = getUtility(IWebhookSet).new(
            target, person, u'http://path/to/something', [self.event_type],
            True, u'sekrit')
        Store.of(hook).flush()
        self.assertEqual(target, hook.target)
        self.assertEqual(person, hook.registrant)
        self.assertIsNot(None, hook.date_created)
        self.assertEqual(hook.date_created, hook.date_last_modified)
        self.assertEqual(u'http://path/to/something', hook.delivery_url)
        self.assertEqual(True, hook.active)
        self.assertEqual(u'sekrit', hook.secret)
        self.assertEqual([self.event_type], hook.event_types)

    def test_getByID(self):
        hook1 = self.factory.makeWebhook()
        hook2 = self.factory.makeWebhook()
        with admin_logged_in():
            self.assertEqual(
                hook1, getUtility(IWebhookSet).getByID(hook1.id))
            self.assertEqual(
                hook2, getUtility(IWebhookSet).getByID(hook2.id))
            self.assertIs(
                None, getUtility(IWebhookSet).getByID(1234))

    def test_findByTarget(self):
        target1 = self.makeTarget()
        target2 = self.makeTarget()
        for target, name in ((target1, 'one'), (target2, 'two')):
            for i in range(3):
                self.factory.makeWebhook(
                    target, u'http://path/%s/%d' % (name, i))
        with person_logged_in(target1.owner):
            self.assertContentEqual(
                [u'http://path/one/0', u'http://path/one/1',
                 u'http://path/one/2'],
                [hook.delivery_url for hook in
                getUtility(IWebhookSet).findByTarget(target1)])
        with person_logged_in(target2.owner):
            self.assertContentEqual(
                [u'http://path/two/0', u'http://path/two/1',
                 u'http://path/two/2'],
                [hook.delivery_url for hook in
                getUtility(IWebhookSet).findByTarget(target2)])

    def test_delete(self):
        target = self.makeTarget()
        login_person(target.owner)
        hooks = []
        for i in range(3):
            hook = self.factory.makeWebhook(target, u'http://path/to/%d' % i)
            hook.ping()
            hooks.append(hook)
        self.assertEqual(3, IStore(WebhookJob).find(WebhookJob).count())
        self.assertContentEqual(
            [u'http://path/to/0', u'http://path/to/1', u'http://path/to/2'],
            [hook.delivery_url for hook in
             getUtility(IWebhookSet).findByTarget(target)])

        transaction.commit()
        with StormStatementRecorder() as recorder:
            getUtility(IWebhookSet).delete(hooks[:2])
        self.assertThat(recorder, HasQueryCount(Equals(4)))

        self.assertContentEqual(
            [u'http://path/to/2'],
            [hook.delivery_url for hook in
             getUtility(IWebhookSet).findByTarget(target)])
        self.assertEqual(1, IStore(WebhookJob).find(WebhookJob).count())
        self.assertEqual(1, hooks[2].deliveries.count())

    def test_trigger(self):
        owner = self.factory.makePerson()
        target1 = self.makeTarget(owner=owner)
        target2 = self.makeTarget(owner=owner)
        hook1a = self.factory.makeWebhook(
            target=target1, event_types=[])
        hook1b = self.factory.makeWebhook(
            target=target1, event_types=[self.event_type])
        hook2a = self.factory.makeWebhook(
            target=target2, event_types=[self.event_type])
        hook2b = self.factory.makeWebhook(
            target=target2, event_types=[self.event_type], active=False)

        # Only webhooks subscribed to the relevant target and event type
        # are triggered.
        getUtility(IWebhookSet).trigger(
            target1, self.event_type, {'some': 'payload'})
        with admin_logged_in():
            self.assertThat(list(hook1a.deliveries), HasLength(0))
            self.assertThat(list(hook1b.deliveries), HasLength(1))
            self.assertThat(list(hook2a.deliveries), HasLength(0))
            self.assertThat(list(hook2b.deliveries), HasLength(0))
            delivery = hook1b.deliveries.one()
            self.assertEqual(delivery.payload, {'some': 'payload'})

        # Disabled webhooks aren't triggered.
        getUtility(IWebhookSet).trigger(
            target2, self.event_type, {'other': 'payload'})
        with admin_logged_in():
            self.assertThat(list(hook1a.deliveries), HasLength(0))
            self.assertThat(list(hook1b.deliveries), HasLength(1))
            self.assertThat(list(hook2a.deliveries), HasLength(1))
            self.assertThat(list(hook2b.deliveries), HasLength(0))
            delivery = hook2a.deliveries.one()
            self.assertEqual(delivery.payload, {'other': 'payload'})


class TestWebhookSetGitRepository(TestWebhookSetBase, TestCaseWithFactory):

    event_type = 'git:push:0.1'

    def makeTarget(self, owner=None):
        return self.factory.makeGitRepository(owner=owner)


class TestWebhookSetBranch(TestWebhookSetBase, TestCaseWithFactory):

    event_type = 'bzr:push:0.1'

    def makeTarget(self, owner=None):
        return self.factory.makeBranch(owner=owner)
