# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Launchpad IDatabaseInteractionPolicy.

The policy connects our Storm stores to either master or replica
databases based on the type of request or if read only mode is in operation.
"""

__metaclass__ = type
__all__ = [
        'LaunchpadDatabasePolicy',
        ]

from zope.interface import implements

import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import (
        IDatabasePolicy, MASTER_FLAVOR, SLAVE_FLAVOR)

class LaunchpadDatabasePolicy:

    implements(IDatabasePolicy)

    def __init__(self, request):
        self.request = request

    def beforeTraversal(self):
        """Install the database policy.

        This method is invoked by
        LaunchpadBrowserPublication.beforeTraversal()
        
        The policy connects our Storm stores to either master or replica
        databases based on the type of request or if read only mode is in
        operation.
        """
        self.read_only = self.request.method in ['GET', 'HEAD']

        # Tell our custom database adapter that the request has started.
        da.set_request_started()

        # Select the default Store. Talking directly to the implementation
        # rather than looking up via the IStoreSelector interface as
        # setDefaultFlavor isn't part of that interface.
        if self.read_only:
            da.StoreSelector.setDefaultFlavor(SLAVE_FLAVOR)
        else:
            da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)

    def endRequest(self):
        """Cleanup.
        
        This method is invoked by LaunchpadBrowserPublication.endRequest.
        """
        da.clear_request_started()

