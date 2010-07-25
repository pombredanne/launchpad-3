# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'FeatureController',
    'per_thread',
    ]


__metaclass__ = type


import threading

from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )


per_thread = threading.local()
"""Holds the default per-thread feature controller in its .features attribute.

Framework code is responsible for setting this in the appropriate context, eg
when starting a web request.
"""


def getFeatureFlag(flag):
    """Get the value of a flag for this thread's scopes.
    """
    return per_thread.features.getFlag(flag)


def summarizeFlags():
    """Nerd-readable summary of active flags (for page footer)"""
    if per_thread.features:
        return repr(per_thread.features.getAllFlags())
    else:
        return "(no FeatureController)"


class FeatureController(object):
    """A FeatureController tells application code what features are active.

    It does this by meshing together two sources of data:
    - feature flags, typically set by an administrator into the database
    - feature scopes, which would typically be looked up based on attributes
      of the current web request, or the user for whom a job is being run, or
      something similar.

    FeatureController presents a high level interface for application code to
    query flag values, without it needing to know that they are stored in the
    database.

    At this level flag names and scope names are presented as strings for
    easier use in Python code, though the values remain unicode.  They
    should always be ascii like Python identifiers.

    One instance of FeatureController should be constructed for the lifetime
    of code that has consistent configuration values.  For instance there will
    be one per web app request.

    Intended performance: when this object is first constructed, it will read
    the whole current feature flags from the database.  This will take a few
    ms.  The controller is then supposed to be held in a thread-local for the
    duration of the request.

    See <https://dev.launchpad.net/LEP/FeatureFlags>
    """

    def __init__(self, scopes):
        """Construct a new view of the features for a set of scopes.
        """
        self._store = getFeatureStore()
        self._scopes = self._preenScopes(scopes)
        self._cached_flags = self._queryAllFlags()

    def getScopes(self):
        return frozenset(self._scopes)

    def getFlag(self, flag_name):
        return self._cached_flags.get(flag_name)

    def getAllFlags(self):
        """Get the feature flags active for the current scopes.

        :returns: dict from flag_name (unicode) to value (unicode).
        """
        return dict(self._cached_flags)

    def _queryAllFlags(self):
        d = {}
        rs = (self._store
                .find(FeatureFlag,
                    FeatureFlag.scope.is_in(self._scopes))
                .order_by(FeatureFlag.priority)
                .values(FeatureFlag.flag, FeatureFlag.value))
        for flag, value in rs:
            d[str(flag)] = value
        return d

    def _preenScopes(self, scopes):
        # for convenience turn strings to unicode
        us = []
        for s in scopes:
            if isinstance(s, unicode):
                us.append(s)
            elif isinstance(s, str):
                us.append(unicode(s))
            else:
                raise TypeError("invalid scope: %r" % s)
        return us
