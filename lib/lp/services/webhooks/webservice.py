# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook webservice registrations."""

__metaclass__ = type

__all__ = [
    'IWebhook',
    'IWebhookDeliveryJob',
    'IWebhookTarget',
    ]

from lp.services.webhooks.interfaces import (
    IWebhook,
    IWebhookDeliveryJob,
    IWebhookTarget,
    )
