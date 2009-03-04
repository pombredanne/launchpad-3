# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Launchpad database policies."""

__metaclass__ = type
__all__ = [
    'LaunchpadDatabasePolicy',
    'SlaveDatabasePolicy',
    'MasterDatabasePolicy',
    ]

from datetime import datetime, timedelta
from textwrap import dedent

from zope.session.interfaces import ISession, IClientIdManager
from zope.component import getUtility
from zope.interface import implements
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from canonical.config import config
from canonical.launchpad.webapp import LaunchpadView
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import (
    ALL_STORES, AUTH_STORE, DEFAULT_FLAVOR,
    IDatabasePolicy, IStoreSelector,
    MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)


def _now():
    """Return current utc time as a datetime with no timezone info.

    This is a global method to allow the test suite to override.
    """
    return datetime.utcnow()


# Can be tweaked by the test suite to simulate replication lag.
_test_lag = None


class BaseDatabasePolicy:
    """Base class for database policies."""
    implements(IDatabasePolicy)

    def __init__(self, request):
        self.request = request

    def afterCall(self):
        """See `IDatabasePolicy`.

        Resets the default flavor and config section. In the app server,
        it isn't necessary to reset the default store as it will just be
        selected the next request. However, changing the default store in
        the middle of a pagetest can break things.
        """
        da.StoreSelector.setGlobalDefaultFlavor(DEFAULT_FLAVOR)
        da.StoreSelector.setConfigSectionName(None)
        da.StoreSelector.setAllowedStores(None)


class MasterDatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that always select the MASTER_FLAVOR.

    This policy is used for XMLRPC and WebService requests which don't
    support session cookies.
    """
    def beforeTraversal(self):
        """See `IDatabasePolicy`."""
        da.StoreSelector.setGlobalDefaultFlavor(MASTER_FLAVOR)


class SlaveDatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that always selects the SLAVE_FLAVOR.

    This policy is used for Feeds requests and other always-read only request.
    """
    def beforeTraversal(self):
        """See `IDatabasePolicy`."""
        da.StoreSelector.setGlobalDefaultFlavor(SLAVE_FLAVOR)


class LaunchpadDatabasePolicy(BaseDatabasePolicy):
    """Default database policy for web requests."""

    def beforeTraversal(self):
        """Install the database policy.

        This method is invoked by
        LaunchpadBrowserPublication.beforeTraversal()

        The policy connects our Storm stores to either master or
        replica databases.
        """
        # Detect if this is a read only request or not.
        self.read_only = self.request.method in ['GET', 'HEAD']

        # If this is a Retry attempt, force use of the master database.
        if getattr(self.request, '_retry_count', 0) > 0:
            da.StoreSelector.setGlobalDefaultFlavor(MASTER_FLAVOR)

        # Select if the DEFAULT_FLAVOR Store will be the master or a
        # slave. We select slave if this is a readonly request, and
        # only readonly requests have been made by this user recently.
        # This ensures that a user will see any changes they just made
        # on the master, despite the fact it might take a while for
        # those changes to propagate to the slave databases.
        elif self.read_only:
            lag = self.getReplicationLag(MAIN_STORE)
            if (lag is not None
                and lag > timedelta(seconds=config.database.max_usable_lag)):
                # Don't use the slave at all if lag is greater than the
                # configured threshold. This reduces replication oddities
                # noticed by users, as well as reducing load on the
                # slave allowing it to catch up quicker.
                da.StoreSelector.setGlobalDefaultFlavor(MASTER_FLAVOR)
            else:
                session_data = ISession(self.request)['lp.dbpolicy']
                last_write = session_data.get('last_write', None)
                now = _now()
                # 'recently' is  2 minutes plus the replication lag.
                recently = timedelta(minutes=2)
                if lag is None:
                    recently = timedelta(minutes=2)
                else:
                    recently = timedelta(minutes=2) + lag
                if last_write is None or last_write < now - recently:
                    da.StoreSelector.setGlobalDefaultFlavor(SLAVE_FLAVOR)
                else:
                    da.StoreSelector.setGlobalDefaultFlavor(MASTER_FLAVOR)
        else:
            da.StoreSelector.setGlobalDefaultFlavor(MASTER_FLAVOR)

    def afterCall(self):
        """Cleanup.

        This method is invoked by LaunchpadBrowserPublication.endRequest.
        """
        if not self.read_only:
            # We need to further distinguish whether it's safe to write to
            # the session, which will be true if the principal is
            # authenticated or if there is already a session cookie hanging
            # around.
            if IUnauthenticatedPrincipal.providedBy(self.request.principal):
                cookie_name = getUtility(IClientIdManager).namespace
                session_available = (
                    cookie_name in self.request.cookies or
                    self.request.response.getCookie(cookie_name) is not None)
            else:
                session_available = True
            if session_available:
                # A non-readonly request has been made. Store this fact in the
                # session. Precision is hard coded at 1 minute (so we don't
                # update the timestamp if it is # no more than 1 minute out of
                # date to avoid unnecessary and expensive write operations).
                # Webservice and XMLRPC clients may not support cookies, so
                # don't mess with their session. Feeds are always read only,
                # and since they run over http, browsers won't send their
                # session key that was set over https, so we don't want to
                # access the session which will overwrite the cookie and log
                # the user out.
                session_data = ISession(self.request)['lp.dbpolicy']
                last_write = session_data.get('last_write', None)
                now = _now()
                if (last_write is None or
                    last_write < now - timedelta(minutes=1)):
                    # set value
                    session_data['last_write'] = now
        super(LaunchpadDatabasePolicy, self).afterCall()

    def getReplicationLag(self, name):
        """Return the replication delay for the named replication set.

        :returns: timedelta, or None if this isn't a replicated environment,
        """
        # Support the test suite hook.
        global _test_lag
        if _test_lag is not None:
            return _test_lag

        # sl_status only gives meaningful results on the origin node.
        store = da.StoreSelector.get(name, MASTER_FLAVOR)
        return store.execute("SELECT replication_lag()").get_one()[0]


class SSODatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` for the single signon servie.

    Only the auth Master and the main Slave are allowed. Requests for
    other Stores raise exceptions.
    """
    def beforeTraversal(self):
        """See `IDatabasePolicy`."""
        da.StoreSelector.setConfigSectionName('sso')
        da.StoreSelector.setDefaultFlavor(AUTH_STORE, MASTER_FLAVOR)
        da.StoreSelector.setDefaultFlavor(MAIN_STORE, SLAVE_FLAVOR)
        da.StoreSelector.setAllowedStores([
            (AUTH_STORE, MASTER_FLAVOR), (MAIN_STORE, SLAVE_FLAVOR)])


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
