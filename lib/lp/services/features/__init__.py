# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""lp.services.features provide dynamically configurable feature flags.

These can be turned on and off by admins, and can affect particular
defined scopes such as "beta users" or "production servers."
"""

import threading


__all__ = [
    'getFeatureFlag',
    'per_thread',
    ]


per_thread = threading.local()
"""Holds the default per-thread feature controller in its .features attribute.

Framework code is responsible for setting this in the appropriate context, eg
when starting a web request.
"""


def getFeatureFlag(flag):
    """Get the value of a flag for this thread's scopes.
    """
    return per_thread.features.getFlag(flag)
