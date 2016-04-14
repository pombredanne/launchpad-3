# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for snap builds."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility

from lp.services.features import getFeatureFlag
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.payload import compose_webhook_payload
from lp.snappy.interfaces.snap import SNAP_WEBHOOKS_FEATURE_FLAG
from lp.snappy.interfaces.snapbuild import ISnapBuild


def snap_build_status_changed(snapbuild, event):
    """Trigger webhooks when snap package build statuses change."""
    if getFeatureFlag(SNAP_WEBHOOKS_FEATURE_FLAG):
        payload = {
            "snap_build": canonical_url(snapbuild, force_local_path=True),
            "action": "status-changed",
            }
        payload.update(compose_webhook_payload(
            ISnapBuild, snapbuild, ["snap", "status"]))
        getUtility(IWebhookSet).trigger(
            snapbuild.snap, "snap:build:0.1", payload)
