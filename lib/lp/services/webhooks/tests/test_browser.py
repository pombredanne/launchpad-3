# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Webhook views."""

__metaclass__ = type

import re

import soupmatchers
from testtools.matchers import (
    MatchesAll,
    Not,
    )

from lp.services.features.testing import FeatureFixture
from lp.testing import (
    BrowserTestCase,
    login_person,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view

add_webhook_tag = soupmatchers.Tag(
    'add webhook', 'a', text='Add webhook',
    attrs={'href': re.compile(r'\+new-webhook$')})
webhook_listing_tag = soupmatchers.Tag(
    'webhook listing', 'table', attrs={'class': 'listing'})
batch_nav_tag = soupmatchers.Tag(
    'batch nav links', 'td', attrs={'class': 'batch-navigation-links'})


class TestWebhooksView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestWebhooksView, self).setUp()
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        self.target = self.factory.makeGitRepository()
        self.owner = self.target.owner
        login_person(self.owner)

    def makeView(self):
        return create_initialized_view(
            self.target, "+webhooks", principal=self.owner)

    def test_empty(self):
        self.assertThat(
            self.makeView()(),
            MatchesAll(
                soupmatchers.HTMLContains(add_webhook_tag),
                Not(soupmatchers.HTMLContains(webhook_listing_tag))))

    def test_few_hooks(self):
        for i in range(3):
            self.factory.makeWebhook(target=self.target)
        self.assertThat(
            self.makeView()(),
            MatchesAll(
                soupmatchers.HTMLContains(
                    add_webhook_tag, webhook_listing_tag),
                Not(soupmatchers.HTMLContains(batch_nav_tag))))

    def test_many_hooks(self):
        for i in range(10):
            self.factory.makeWebhook(target=self.target)
        self.assertThat(
            self.makeView()(),
            soupmatchers.HTMLContains(
                add_webhook_tag, webhook_listing_tag,
                batch_nav_tag))
