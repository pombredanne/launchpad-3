# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Connect Feature flags into webapp requests."""

__all__ = []

__metaclass__ = type

import canonical.config

from lp.services.features.flags import (
    FeatureController,
    per_thread,
    )


class ScopesFromRequest(object):
    """Identify feature scopes based on request state."""

    def __init__(self, request):
        self._request = request

    def lookup(self, scope_name):
        parts = scope_name.split('.')
        if len(parts) == 2 and parts[0] == 'server':
            return canonical.config.config['launchpad']['is_' + parts[1]]


def start_request(event):
    """Register FeatureController."""
    # TODO: determine all the interesting scopes, based on event.request
    event.request.features = per_thread.features = FeatureController(
        ScopesFromRequest(event.request).lookup)


def end_request(event):
    """Done with this FeatureController."""
    event.request.features = per_thread.features = None
