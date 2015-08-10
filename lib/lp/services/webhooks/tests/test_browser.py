# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Webhook views."""

__metaclass__ = type

import re

import soupmatchers
from testtools.matchers import (
    Equals,
    MatchesAll,
    MatchesStructure,
    Not,
    )
import transaction

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    login_person,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_view

breadcrumbs_tag = soupmatchers.Tag(
    'breadcrumbs', 'ol', attrs={'class': 'breadcrumbs'})
webhooks_page_crumb_tag = soupmatchers.Tag(
    'webhooks page breadcrumb', 'li', text=re.compile('Webhooks'))
webhooks_collection_crumb_tag = soupmatchers.Tag(
    'webhooks page breadcrumb', 'a', text=re.compile('Webhooks'),
    attrs={'href': re.compile(r'/\+webhooks$')})
add_webhook_tag = soupmatchers.Tag(
    'add webhook', 'a', text='Add webhook',
    attrs={'href': re.compile(r'/\+new-webhook$')})
webhook_listing_constants = soupmatchers.HTMLContains(
    soupmatchers.Within(breadcrumbs_tag, webhooks_page_crumb_tag),
    add_webhook_tag)

webhook_listing_tag = soupmatchers.Tag(
    'webhook listing', 'table', attrs={'class': 'listing'})
batch_nav_tag = soupmatchers.Tag(
    'batch nav links', 'td', attrs={'class': 'batch-navigation-links'})


class WebhookTargetViewTestHelpers:

    def setUp(self):
        super(WebhookTargetViewTestHelpers, self).setUp()
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        self.target = self.factory.makeGitRepository()
        self.owner = self.target.owner
        login_person(self.owner)

    def makeView(self, name, **kwargs):
        view = create_view(self.target, name, principal=self.owner, **kwargs)
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [
            self.target.target, self.target, view]
        view.initialize()
        return view


class TestWebhooksView(WebhookTargetViewTestHelpers, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeHooksAndMatchers(self, count):
        hooks = [
            self.factory.makeWebhook(
                target=self.target, delivery_url=u'http://example.com/%d' % i)
            for i in range(count)]
        # There is a link to each webhook.
        link_matchers = [
            soupmatchers.Tag(
                "webhook link", "a", text=hook.delivery_url,
                attrs={
                    "href": canonical_url(hook, path_only_if_possible=True)})
            for hook in hooks]
        return link_matchers

    def test_empty(self):
        # The table isn't shown if there are no webhooks yet.
        self.assertThat(
            self.makeView("+webhooks")(),
            MatchesAll(
                webhook_listing_constants,
                Not(soupmatchers.HTMLContains(webhook_listing_tag))))

    def test_few_hooks(self):
        # The table is just a simple table if there is only one batch.
        link_matchers = self.makeHooksAndMatchers(3)
        self.assertThat(
            self.makeView("+webhooks")(),
            MatchesAll(
                webhook_listing_constants,
                soupmatchers.HTMLContains(webhook_listing_tag, *link_matchers),
                Not(soupmatchers.HTMLContains(batch_nav_tag))))

    def test_many_hooks(self):
        # Batch navigation controls are shown once there are enough.
        link_matchers = self.makeHooksAndMatchers(10)
        self.assertThat(
            self.makeView("+webhooks")(),
            MatchesAll(
                webhook_listing_constants,
                soupmatchers.HTMLContains(
                    webhook_listing_tag, batch_nav_tag, *link_matchers[:5]),
                Not(soupmatchers.HTMLContains(*link_matchers[5:]))))

    def test_query_count(self):
        # The query count is constant with number of webhooks.
        def create_webhook():
            self.factory.makeWebhook(target=self.target)

        # Run once to get things stable, then check that adding more
        # webhooks doesn't inflate the count.
        self.makeView("+webhooks")()
        recorder1, recorder2 = record_two_runs(
            lambda: self.makeView("+webhooks")(), create_webhook, 10)
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))


class TestWebhookAddView(WebhookTargetViewTestHelpers, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        self.assertThat(
            self.makeView("+new-webhook")(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag, webhooks_collection_crumb_tag),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'add webhook breadcrumb', 'li',
                        text=re.compile('Add webhook'))),
                soupmatchers.Tag(
                    'cancel link', 'a', text='Cancel',
                    attrs={'href': re.compile(r'/\+webhooks$')})))

    def test_creates(self):
        view = self.makeView(
            "+new-webhook", method="POST",
            form={
                "field.delivery_url": "http://example.com/test",
                "field.active": "on", "field.event_types-empty-marker": "1",
                "field.event_types": "git:push:0.1",
                "field.actions.new": "Add webhook"})
        self.assertEqual([], view.errors)
        hook = self.target.webhooks.one()
        self.assertThat(
            hook,
            MatchesStructure.byEquality(
                target=self.target,
                registrant=self.owner,
                delivery_url="http://example.com/test",
                active=True,
                event_types=["git:push:0.1"]))

    def test_rejects_bad_scheme(self):
        transaction.commit()
        view = self.makeView(
            "+new-webhook", method="POST",
            form={
                "field.delivery_url": "ftp://example.com/test",
                "field.active": "on", "field.event_types-empty-marker": "1",
                "field.actions.new": "Add webhook"})
        self.assertEqual(
            ['delivery_url'], [error.field_name for error in view.errors])
        self.assertIs(None, self.target.webhooks.one())


class WebhookViewTestHelpers:

    def setUp(self):
        super(WebhookViewTestHelpers, self).setUp()
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        self.target = self.factory.makeGitRepository()
        self.owner = self.target.owner
        self.webhook = self.factory.makeWebhook(
            target=self.target, delivery_url=u'http://example.com/original')
        login_person(self.owner)

    def makeView(self, name, **kwargs):
        view = create_view(self.webhook, name, principal=self.owner, **kwargs)
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [
            self.target.target, self.target, self.webhook, view]
        view.initialize()
        return view


class TestWebhookView(WebhookViewTestHelpers, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        self.assertThat(
            self.makeView("+index")(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag, webhooks_collection_crumb_tag),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'webhook breadcrumb', 'li',
                        text=re.compile(re.escape(
                            self.webhook.delivery_url)))),
                soupmatchers.Tag(
                    'delete link', 'a', text='Delete webhook',
                    attrs={'href': re.compile(r'/\+delete$')})))

    def test_saves(self):
        view = self.makeView(
            "+index", method="POST",
            form={
                "field.delivery_url": "http://example.com/edited",
                "field.active": "off", "field.event_types-empty-marker": "1",
                "field.actions.save": "Save webhook"})
        self.assertEqual([], view.errors)
        self.assertThat(
            self.webhook,
            MatchesStructure.byEquality(
                delivery_url="http://example.com/edited",
                active=False,
                event_types=[]))

    def test_rejects_bad_scheme(self):
        transaction.commit()
        view = self.makeView(
            "+index", method="POST",
            form={
                "field.delivery_url": "ftp://example.com/edited",
                "field.active": "off", "field.event_types-empty-marker": "1",
                "field.actions.save": "Save webhook"})
        self.assertEqual(
            ['delivery_url'], [error.field_name for error in view.errors])
        self.assertThat(
            self.webhook,
            MatchesStructure.byEquality(
                delivery_url="http://example.com/original",
                active=True,
                event_types=[]))


class TestWebhookDeleteView(WebhookViewTestHelpers, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        self.assertThat(
            self.makeView("+delete")(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag, webhooks_collection_crumb_tag),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'webhook breadcrumb', 'a',
                        text=re.compile(re.escape(
                            self.webhook.delivery_url)),
                        attrs={'href': canonical_url(self.webhook)})),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'delete breadcrumb', 'li',
                        text=re.compile('Delete webhook'))),
                soupmatchers.Tag(
                    'cancel link', 'a', text='Cancel',
                    attrs={'href': canonical_url(self.webhook)})))

    def test_deletes(self):
        view = self.makeView(
            "+delete", method="POST",
            form={"field.actions.delete": "Delete webhook"})
        self.assertEqual([], view.errors)
        self.assertIs(None, self.target.webhooks.one())
