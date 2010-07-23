# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Connect Feature flags into webapp requests."""

__all__ = []

__metaclass__ = type

from lp.services.features.flags import (
    FeatureController,
    per_thread,
    )


def start_request(event):
    """Register FeatureController."""
    # TODO: determine all the interesting scopes, based on event.request
    per_thread.features = FeatureController(['default'])


def end_request(event):
    """Done with this FeatureController."""
    per_thread.features = None
