# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook browser and API classes."""

__metaclass__ = type

__all__ = [
    'WebhookTargetNavigationMixin',
    ]

from zope.component import getUtility

from lp.services.webapp import stepthrough
from lp.services.webhooks.interfaces import IWebhookSource


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
