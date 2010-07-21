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

    This presents a higher-level interface over the storm model objects,
    oriented only towards readers.
    """

    def __init__(self):
        self._collection = model.FeatureFlagCollection()

    def getAllFlags(self):
        """Get the feature flags active for the current context.
        
        :returns: dict from flag_name (unicode) to value (unicode).
        """
        rs = self._collection.select().order_by(
            Desc(model.FeatureFlag.priority))
        l = dict((f.flag, f.value) for f in rs)
        return l

    def getFlagsForScopes(self, scopes):
        """Get flags for specified set of scopes.
        """
        # for convenience turn strings to unicode
        us = []
        for s in scopes:
            if isinstance(s, unicode):
                us.append(s)
            elif isinstance(s, str):
                us.append(unicode(s))
            else:
                raise TypeError("invalid scope: %r" % s)
        rs = self._collection.refine(
            model.FeatureFlag.scope.is_in(us)).select()
        rs = rs.order_by(
            Desc(model.FeatureFlag.priority))
        return dict((f.flag, f.value) for f in rs)

    def addSetting(self, **kwargs):
        flag = model.FeatureFlag(**kwargs)
        self._collection.store.add(flag)
