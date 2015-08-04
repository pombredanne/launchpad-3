# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook browser and API classes."""

__metaclass__ = type

__all__ = [
    'WebhookNavigation',
    'WebhookTargetNavigationMixin',
    ]

from lazr.restful.interface import use_template
from zope.component import getUtility
from zope.interface import Interface

from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    Navigation,
    stepthrough,
    )
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webhooks.interfaces import (
    IWebhook,
    IWebhookSource,
    )


class WebhookNavigation(Navigation):

    usedfor = IWebhook

    @stepthrough('+delivery')
    def traverse_delivery(self, id):
        try:
            id = int(id)
        except ValueError:
            return None
        return self.context.getDelivery(id)


class WebhookTargetNavigationMixin:

    @stepthrough('+webhook')
    def traverse_webhook(self, id):
        try:
            id = int(id)
        except ValueError:
            return None
        webhook = getUtility(IWebhookSource).getByID(id)
        if webhook is None or webhook.target != self.context:
            return None
        return webhook


class WebhooksView(LaunchpadView):

    @property
    def page_title(self):
        return "Webhooks"

    @property
    def label(self):
        return "Webhooks for %s" % self.context.display_name

    @cachedproperty
    def batchnav(self):
        return BatchNavigator(
            getUtility(IWebhookSource).findByTarget(self.context),
            self.request)


class WebhooksBreadcrumb(Breadcrumb):

    text = "Webhooks"

    @property
    def url(self):
        return canonical_url(self.context, view_name="+webhooks")

    @property
    def inside(self):
        return self.context


class WebhookBreadcrumb(Breadcrumb):

    @property
    def text(self):
        return self.context.delivery_url

    @property
    def inside(self):
        return WebhooksBreadcrumb(self.context.target)


class WebhookEditSchema(Interface):
    # XXX wgrant 2015-08-04: Need custom widgets for secret and
    # event_types.
    use_template(IWebhook, include=['delivery_url', 'event_types', 'active'])


class WebhookAddView(LaunchpadFormView):

    page_title = label = "Add webhook"

    schema = WebhookEditSchema

    @property
    def inside_breadcrumb(self):
        return WebhooksBreadcrumb(self.context)

    @property
    def initial_values(self):
        return {'active': True}

    @property
    def cancel_url(self):
        return canonical_url(self.context, view_name="+webhooks")

    @action("Add webhook", name="new")
    def new_action(self, action, data):
        webhook = self.context.newWebhook(
            registrant=self.user, delivery_url=data['delivery_url'],
            event_types=data['event_types'], active=data['active'])
        self.next_url = canonical_url(webhook)


class WebhookView(LaunchpadEditFormView):

    schema = WebhookEditSchema

    label = "Manage webhook"

    @property
    def next_url(self):
        # The edit form is the default view, so the URL doesn't need the
        # normal view name suffix.
        return canonical_url(self.context)

    @property
    def adapters(self):
        return {self.schema: self.context}

    @action("Save webhook", name="save")
    def save_action(self, action, data):
        self.updateContextFromData(data)


class WebhookDeleteView(LaunchpadFormView):

    schema = Interface

    page_title = label = "Delete webhook"

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action("Delete webhook", name="delete")
    def delete_action(self, action, data):
        target = self.context.target
        self.context.destroySelf()
        self.request.response.addNotification(
            "Webhook for %s deleted." % self.context.delivery_url)
        self.next_url = canonical_url(target, view_name="+webhooks")
