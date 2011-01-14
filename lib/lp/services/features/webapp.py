# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Connect Feature flags into webapp requests."""

__all__ = []

__metaclass__ = type

from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.services.features import per_thread
from lp.services.features.flags import FeatureController
from lp.services.features.rulesource import StormFeatureRuleSource
from lp.services.features.scopes import ScopesFromRequest


def start_request(event):
    """Register FeatureController."""
    event.request.features = per_thread.features = FeatureController(
        ScopesFromRequest(event.request).lookup,
        StormFeatureRuleSource())


def end_request(event):
    """Done with this FeatureController."""
    event.request.features = per_thread.features = None
