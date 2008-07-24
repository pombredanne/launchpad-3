# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Launchpad IDatabaseInteractionPolicy."""

__metaclass__ = type
__all__ = [
        'LaunchpadDatabasePolicy',
        ]

from datetime import datetime, timedelta

from zope.app.session.interfaces import ISession
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
        
        The policy connects our Storm stores to either master or
        replica databases.
        """
        # Detect if this is a read only request or not.
        self.read_only = self.request.method in ['GET', 'HEAD']

        # Select if the DEFAULT_FLAVOR Store will be the master or a
        # slave. We select slave if this is a readonly request, and
        # only readonly requests have been made by this user recently.
        # This ensures that a user will see any changes they just made
        # on the master, despite the fact it might take a while for
        # those changes to propagate to the slave databases.
        if self.read_only:
            session_data = ISession(self.request)['lp.dbpolicy']
            last_write = session_data.get('last_write', None)
            now = datetime.utcnow()
            # 'recently' is hardcoded at 5 minutes.
            if last_write is None or last_write < now - timedelta(minutes=5):
                da.StoreSelector.setDefaultFlavor(SLAVE_FLAVOR)
            else:
                da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)
        else:
            da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)

    def endRequest(self):
        """Cleanup.
        
        This method is invoked by LaunchpadBrowserPublication.endRequest.
        """
        if not self.read_only:
            # A non-readonly request has been made. Store this fact
            # in the session. Precision is hard coded at 1 minute.
            session_data = ISession(self.request)['lp.dbpolicy']
            last_write = session_data.get('last_write', None)
            now = datetime.utcnow()
            if last_write is None or last_write < now - timedelta(minutes=1):
                session_data['last_write'] = now

