# Copyright 2016-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for snap builds."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.services.features import getFeatureFlag
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.payload import compose_webhook_payload
from lp.snappy.interfaces.snap import SNAP_WEBHOOKS_FEATURE_FLAG
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.snappy.interfaces.snapbuildjob import ISnapStoreUploadJobSource


def _trigger_snap_build_webhook(snapbuild):
    if getFeatureFlag(SNAP_WEBHOOKS_FEATURE_FLAG):
        payload = {
            "snap_build": canonical_url(snapbuild, force_local_path=True),
            "action": "status-changed",
            }
        payload.update(compose_webhook_payload(
            ISnapBuild, snapbuild, ["snap", "status", "store_upload_status"]))
        getUtility(IWebhookSet).trigger(
            snapbuild.snap, "snap:build:0.1", payload)


def snap_build_status_changed(snapbuild, event):
    """Trigger events when snap package build statuses change."""
    _trigger_snap_build_webhook(snapbuild)

    if (snapbuild.snap.can_upload_to_store and snapbuild.snap.store_upload and
            snapbuild.status == BuildStatus.FULLYBUILT):
        getUtility(ISnapStoreUploadJobSource).create(snapbuild)


def snap_build_store_upload_status_changed(snapbuild, event):
    """Trigger events when snap package build store upload statuses change."""
    _trigger_snap_build_webhook(snapbuild)
