# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Launchpad database policies."""

__metaclass__ = type
__all__ = [
    'LaunchpadDatabasePolicy',
    'SlaveDatabasePolicy',
    'SSODatabasePolicy',
    'MasterDatabasePolicy',
    ]

from datetime import datetime, timedelta
from textwrap import dedent

from storm.zope.interfaces import IZStorm
from zope.session.interfaces import ISession, IClientIdManager
from zope.component import getUtility
from zope.interface import implements, alsoProvides
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from canonical.config import config, dbconfig
from canonical.launchpad.interfaces import IMasterStore, ISlaveStore
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.interfaces import (
    AUTH_STORE, DEFAULT_FLAVOR, DisallowedStore,
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

    # The section name to retrieve database connection details from.
    # None means the default.
    config_section = None

    # The default flavor to use.
    default_flavor = MASTER_FLAVOR

    def __init__(self, request=None):
        pass

    def getStore(self, name, flavor):
        """See `IDatabasePolicy`."""
        if flavor == DEFAULT_FLAVOR:
            flavor = self.default_flavor

        config_section = self.config_section or dbconfig.getSectionName()

        store = getUtility(IZStorm).get(
            '%s-%s-%s' % (config_section, name, flavor),
            'launchpad:%s-%s-%s' % (config_section, name, flavor))

        # Attach our marker interfaces so our adapters don't lie.
        if flavor == MASTER_FLAVOR:
            alsoProvides(store, IMasterStore)
        else:
            alsoProvides(store, ISlaveStore)

        return store

    def install(self, request=None):
        """See `IDatabasePolicy`."""
        pass

    def uninstall(self):
        """See `IDatabasePolicy`."""
        pass


class MasterDatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that selects the MASTER_FLAVOR by default.

    Slave databases can still be accessed if requested explicitly.

    This policy is used for XMLRPC and WebService requests which don't
    support session cookies. It is also used when no policy has been
    installed.
    """
    default_flavor = MASTER_FLAVOR


class SlaveDatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that selects the SLAVE_FLAVOR by default.

    Access to a master can still be made if requested explicitly.
    """
    default_flavor = SLAVE_FLAVOR


class SlaveOnlyDatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that only allows access to SLAVE_FLAVOR stores.

    This policy is used for Feeds requests and other always-read only request.
    """
    default_flavor = SLAVE_FLAVOR
    def getStore(self, name, flavor):
        """See `IDatabasePolicy`."""
        if flavor == MASTER_FLAVOR:
            raise DisallowedStore(flavor)
        return super(SlaveOnlyDatabasePolicy, self).getStore(
            name, SLAVE_FLAVOR)


class LaunchpadDatabasePolicy(BaseDatabasePolicy):
    """Default database policy for web requests.

    Selects the DEFAULT_FLAVOR based on the request.
    """
    def __init__(self, request):
        self.request = request

    def install(self):
        """See `IDatabasePolicy`."""
        # Detect if this is a read only request or not.
        self.read_only = self.request.method in ['GET', 'HEAD']

        default_flavor = None

        # If this is a Retry attempt, force use of the master database.
        if getattr(self.request, '_retry_count', 0) > 0:
            default_flavor = MASTER_FLAVOR

        # Select if the DEFAULT_FLAVOR Store will be the master or a
        # slave. We select slave if this is a readonly request, and
        # only readonly requests have been made by this user recently.
        # This ensures that a user will see any changes they just made
        # on the master, despite the fact it might take a while for
        # those changes to propagate to the slave databases.
        elif self.read_only:
            lag = self.getReplicationLag()
            if (lag is not None
                and lag > timedelta(seconds=config.database.max_usable_lag)):
                # Don't use the slave at all if lag is greater than the
                # configured threshold. This reduces replication oddities
                # noticed by users, as well as reducing load on the
                # slave allowing it to catch up quicker.
                default_flavor = MASTER_FLAVOR
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
                    default_flavor = SLAVE_FLAVOR
                else:
                    default_flavor = MASTER_FLAVOR
        else:
            default_flavor = MASTER_FLAVOR

        assert default_flavor is not None, 'default_flavor not set!'

        self.default_flavor = default_flavor

    def uninstall(self):
        """See `IDatabasePolicy`.

        If the request just handled was not read_only, we need to store
        this fact and the timestamp in the session. Subsequent requests
        can then keep using the master until they are sure any changes
        made have been propagated.
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

    def getReplicationLag(self):
        """Return the replication lag.

        :returns: timedelta, or None if this isn't a replicated environment,
        """
        # Support the test suite hook.
        if _test_lag is not None:
            return _test_lag

        # sl_status gives the best results on the origin node.
        store = self.getStore(MAIN_STORE, MASTER_FLAVOR)
        return store.execute("SELECT replication_lag()").get_one()[0]


class SSODatabasePolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` for the single signon servie.

    Only the auth Master and the main Slave are allowed. Requests for
    other Stores raise DisallowedStore exceptions.
    """
    config_section = 'sso'

    def getStore(self, name, flavor):
        """See `IDatabasePolicy`."""
        if name == AUTH_STORE:
            if flavor == SLAVE_FLAVOR:
                raise DisallowedStore(name, flavor)
            flavor = MASTER_FLAVOR
        elif name == MAIN_STORE:
            if flavor == MASTER_FLAVOR:
                raise DisallowedStore(name, flavor)
            flavor = SLAVE_FLAVOR
        else:
            raise DisallowedStore(name, flavor)

        return super(SSODatabasePolicy, self).getStore(name, flavor)


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
