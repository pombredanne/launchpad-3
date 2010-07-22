# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['FeatureController']

__metaclass__ = type


from lp.services.features import model

from storm.locals import (
    Desc,
    )


# Intended performance: when this object is first constructed, it will read
# the whole current feature flags from the database.  This will take a few ms.
# The controller is then supposed to be held in a thread-local for the
# duration of the request.  The scopes can be changed over the lifetime of the
# controller, because we might not know enough to determine all the active
# scopes when the object's first created.   This isn't validated to work yet.
    

class FeatureController(object):
    """A FeatureController tells application code what features are active.

    It does this by meshing together two sources of data: 
    - feature flags, typically set by an administrator into the database
    - feature scopes, which would typically be looked up based on attributes 
      of the current web request, or the user for whom a job is being run, or
      something similar.

    This presents a higher-level facade that is independent of how the flags
    are stored.  At the moment they are stored in the database but callers
    shouldn't need to know about that: they could go into memcachedb or
    elsewhere in future.

    At this level flag names and scope names are presented as strings for
    easier use in Python code, though the values remain unicode.  They
    should always be ascii like Python identifiers.

    One instance of this should be constructed for the lifetime of code that
    has consistent configuration values.  For instance there will be one per web
    app request.

    See <https://dev.launchpad.net/LEP/FeatureFlags>
    """

    def __init__(self, scopes):
        """Construct a new view of the features for a set of scopes.
        """
        self._store = model.getFeatureStore()
        self.scopes = self._preenScopes(scopes)

    def setScopes(self, scopes):
        self.scopes = self._preenScopes(scopes)

    def getFlag(self, flag_name):
        rs = (self._store
                .find(model.FeatureFlag,
                    model.FeatureFlag.scope.is_in(self.scopes),
                    model.FeatureFlag.flag == unicode(flag_name))
                .order_by(Desc(model.FeatureFlag.priority)))
        row = rs.first()
        if row is None:
            return None
        else:
            return row.value

    def getAllFlags(self):
        """Get the feature flags active for the current scopes.
        
        :returns: dict from flag_name (unicode) to value (unicode).
        """
        rs = (self._store
                .find(model.FeatureFlag,
                    model.FeatureFlag.scope.is_in(self.scopes))
                .order_by(model.FeatureFlag.priority))
        return dict((str(f.flag), f.value) for f in rs)

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

    def addSetting(self, scope, flag, value, priority):
        """Add a setting for a flag.

        Note that flag settings are global in the database: they affect all
        FeatureControllers connected to this database, and they will persist
        if the database transaction is committed.
        """
        flag_obj = model.FeatureFlag(scope=unicode(scope),
            flag=unicode(flag),
            value=value,
            priority=priority)
        self._store.add(flag_obj)
