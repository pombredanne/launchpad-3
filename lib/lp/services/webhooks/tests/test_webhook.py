# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from storm.store import Store
from zope.component import getUtility

from lp.services.webhooks.interfaces import IWebhookSource
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestWebhookSource(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_new(self):
        target = self.factory.makeGitRepository()
        person = self.factory.makePerson()
        hook = getUtility(IWebhookSource).new(
            target, person, u'http://path/to/something', True, u'sekrit')
        Store.of(hook).flush()
        self.assertEqual(target, hook.target)
        self.assertEqual(person, hook.registrant)
        self.assertIsNot(None, hook.date_created)
        self.assertEqual(hook.date_created, hook.date_last_modified)
        self.assertEqual(u'http://path/to/something', hook.endpoint_url)
        self.assertEqual(True, hook.active)
        self.assertEqual(u'sekrit', hook.secret)

    def test_getByID(self):
        hook1 = self.factory.makeWebhook()
        hook2 = self.factory.makeWebhook()
        self.assertEqual(hook1, getUtility(IWebhookSource).getByID(hook1.id))
        self.assertEqual(hook2, getUtility(IWebhookSource).getByID(hook2.id))
        self.assertIs(None, getUtility(IWebhookSource).getByID(1234))

    def test_findByTarget(self):
        target1 = self.factory.makeGitRepository()
        target2 = self.factory.makeGitRepository()
        for target, name in ((target1, 'one'), (target2, 'two')):
            for i in range(3):
                self.factory.makeWebhook(
                    target, u'http://path/%s/%d' % (name, i))
        self.assertContentEqual(
            [u'http://path/one/0', u'http://path/one/1', u'http://path/one/2'],
            [hook.endpoint_url for hook in
             getUtility(IWebhookSource).findByTarget(target1)])
        self.assertContentEqual(
            [u'http://path/two/0', u'http://path/two/1', u'http://path/two/2'],
            [hook.endpoint_url for hook in
             getUtility(IWebhookSource).findByTarget(target2)])

    def test_delete(self):
        target = self.factory.makeGitRepository()
        hooks = [
            self.factory.makeWebhook(target, u'http://path/to/%d' % i)
            for i in range(3)]
        self.assertContentEqual(
            [u'http://path/to/0', u'http://path/to/1', u'http://path/to/2'],
            [hook.endpoint_url for hook in
             getUtility(IWebhookSource).findByTarget(target)])
        getUtility(IWebhookSource).delete(hooks[:2])
        self.assertContentEqual(
            [u'http://path/to/2'],
            [hook.endpoint_url for hook in
             getUtility(IWebhookSource).findByTarget(target)])
