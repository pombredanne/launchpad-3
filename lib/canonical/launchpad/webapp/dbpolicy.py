# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Launchpad IDatabaseInteractionPolicy."""

__metaclass__ = type
__all__ = [
    'LaunchpadDatabasePolicy',
    ]

from datetime import datetime, timedelta
from textwrap import dedent

from zope.session.interfaces import ISession
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest

from canonical.launchpad.layers import FeedsLayer, WebServiceLayer
from canonical.launchpad.webapp import LaunchpadView
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import (
    IDatabasePolicy, IStoreSelector,
    MAIN_STORE, DEFAULT_FLAVOR, MASTER_FLAVOR, SLAVE_FLAVOR)


def _now():
    """Return current utc time as a datetime with no timezone info.

    This is a global method to allow the test suite to override.
    """
    return datetime.utcnow()


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
        if FeedsLayer.providedBy(self.request):
            # We don't want the feeds layer to access the
            # session since the cookie set by vhosts using ssl
            # will not get passed into the feeds vhost because it
            # doesn't use ssl. Since it doesn't see the cookie for
            # the current session, it will create a new cookie which
            # overwrites the https cookie.
            da.StoreSelector.setDefaultFlavor(SLAVE_FLAVOR)
        elif self.read_only:
            if WebServiceLayer.providedBy(self.request):
                # Don't bother checking the session for a webservice request,
                # since we don't even set the session in the afterCall()
                # method.
                last_write = None
            else:
                session_data = ISession(self.request)['lp.dbpolicy']
                last_write = session_data.get('last_write', None)
                now = _now()
            # 'recently' is  2 minutes plus the replication lag.
            recently = timedelta(minutes=2)
            lag = self.getReplicationLag(MAIN_STORE)
            if lag is None:
                recently = timedelta(minutes=2)
            else:
                recently = timedelta(minutes=2) + lag
            if last_write is None or last_write < now - recently:
                da.StoreSelector.setDefaultFlavor(SLAVE_FLAVOR)
            else:
                da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)
        else:
            da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)

    def afterCall(self):
        """Cleanup.

        This method is invoked by LaunchpadBrowserPublication.endRequest.
        """
        if (not self.read_only
            and not WebServiceLayer.providedBy(self.request)
            and not FeedsLayer.providedBy(self.request)
            and not IXMLRPCRequest.providedBy(self.request)):
            # A non-readonly request has been made. Store this fact in
            # the session. Precision is hard coded at 1 minute (so we
            # don't update the timestamp if it is # no more than 1 minute
            # out of date to avoid unnecessary and expensive write
            # operations).
            # Webservice and XMLRPC clients may not support cookies,
            # so don't mess with their session.
            # Feeds are always read only, and since they run over http,
            # browsers won't send their session key that was set over https,
            # so we don't want to access the session which will overwrite
            # the cookie and log the user out.
            session_data = ISession(self.request)['lp.dbpolicy']
            last_write = session_data.get('last_write', None)
            now = _now()
            if last_write is None or last_write < now - timedelta(minutes=1):
                session_data['last_write'] = now
        # For the webapp, it isn't necessary to reset the default store as
        # it will just be selected the next request. However, changing the
        # default store in the middle of a pagetest can break things.
        da.StoreSelector.setDefaultFlavor(MASTER_FLAVOR)

    def getReplicationLag(self, name):
        """Return the replication delay for the named replication set.
       
        :returns: timedelta, or None if this isn't a replicated environment,
        """
        # sl_status only gives meaningful results on the origin node.
        store = da.StoreSelector.get(name, MASTER_FLAVOR)
        return store.execute("SELECT replication_lag()").get_one()[0]


class WhichDbView(LaunchpadView):
    "A page that reports which database is being used by default."
    def render(self):
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        dbname = store.execute("SELECT current_database()").get_one()[0]
        return dedent("""
                <html>
                <body>
                <span id="dbname">
                %s
                </span>
                <form method="post">
                <input type="submit" value="Do Post" />
                </form>
                </body>
                </html>
                """ % dbname).strip()

