# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['FeatureController']

__metaclass__ = type


class FeatureController(object):
    """A FeatureController tells application code what features are active.

    It does this by meshing together two sources of data: 
    - feature flags, typically set by an administrator into the database
    - feature scopes, which would typically be looked up based on attributes 
      of the current web request, or the user for whom a job is being run, or
      something similar.

    For testing purposes, either or both of these can be taken from in-memory
    objects.

    Performance: when this object is first constructed, it will read the whole
    current feature flags from the database.  This will take a few ms.  The
    controller is then supposed to be held in a thread-local for the duration
    of the request.  The scopes can be changed over the lifetime of the
    controller, because we might not know enough to determine all the active
    scopes when the object's first created.  
    
    """

    def getActiveFlags(self):
        """Get the feature flags active for the current context.
        
        :returns: dict from flag_name (string) to value (unicode).
        """

        return {}
