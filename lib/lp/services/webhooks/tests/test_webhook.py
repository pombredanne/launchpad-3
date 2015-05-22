# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from storm.store import Store
from zope.component import getUtility

from lp.services.webhooks.interfaces import IWebhookSource
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestWebhook(TestCaseWithFactory):

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
