# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad database policies."""

__metaclass__ = type
__all__ = [
    'BaseDatabasePolicy',
    'DatabaseBlockedPolicy',
    'LaunchpadDatabasePolicy',
    'MasterDatabasePolicy',
    'ReadOnlyLaunchpadDatabasePolicy',
    'SlaveDatabasePolicy',
    'SlaveOnlyDatabasePolicy',
    ]

from datetime import (
    datetime,
    timedelta,
    )
import logging
from textwrap import dedent

from storm.cache import (
    Cache,
    GenerationalCache,
    )
from storm.zope.interfaces import IZStorm
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.component import getUtility
from zope.interface import (
    alsoProvides,
    implements,
    )
from zope.session.interfaces import (
    IClientIdManager,
    ISession,
    )

from canonical.config import (
    config,
    dbconfig,
    )
from canonical.database.sqlbase import StupidCache
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    ISlaveStore,
    )
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    DisallowedStore,
    IDatabasePolicy,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    ReadOnlyModeDisallowedStore,
    SLAVE_FLAVOR,
    )


def _now():
    """Return current utc time as a datetime with no timezone info.

    This is a global method to allow the test suite to override.
    """
    return datetime.utcnow()


# Can be tweaked by the test suite to simulate replication lag.
_test_lag = None


def storm_cache_factory():
    """Return a Storm Cache of the type and size specified in dbconfig."""
    if dbconfig.storm_cache == 'generational':
        return GenerationalCache(int(dbconfig.storm_cache_size))
    elif dbconfig.storm_cache == 'stupid':
        return StupidCache(int(dbconfig.storm_cache_size))
    elif dbconfig.storm_cache == 'default':
        return Cache(int(dbconfig.storm_cache_size))
    else:
        assert False, "Unknown storm_cache %s." % dbconfig.storm_cache


class BaseDatabasePolicy:
    """Base class for database policies."""
    implements(IDatabasePolicy)

    # The default flavor to use.
    default_flavor = MASTER_FLAVOR

    def __init__(self, request=None):
        pass

    def getStore(self, name, flavor):
        """See `IDatabasePolicy`."""
        if flavor == DEFAULT_FLAVOR:
            flavor = self.default_flavor

        store_name = '%s-%s' % (name, flavor)
        store = getUtility(IZStorm).get(
            store_name, 'launchpad:%s' % store_name)
        if not getattr(store, '_lp_store_initialized', False):
            # No existing Store. Create a new one and tweak its defaults.

            # XXX stub 2009-06-25 bug=391996: The default Storm
            # Cache is useless to a project like Launchpad. Because we
            # are using ZStorm to manage our Stores there is no API
            # available to change the default. Instead, we monkey patch.
            store._cache = storm_cache_factory()

            # Attach our marker interfaces so our adapters don't lie.
            if flavor == MASTER_FLAVOR:
                alsoProvides(store, IMasterStore)
            else:
                alsoProvides(store, ISlaveStore)

            store._lp_store_initialized = True

        return store

    def install(self, request=None):
        """See `IDatabasePolicy`."""
        pass

    def uninstall(self):
        """See `IDatabasePolicy`."""
        pass

    def __enter__(self):
        """See `IDatabasePolicy`."""
        getUtility(IStoreSelector).push(self)

    def __exit__(self, exc_type, exc_value, traceback):
        """See `IDatabasePolicy`."""
        policy = getUtility(IStoreSelector).pop()
        assert policy is self, (
            "Unexpected database policy %s returned by store selector"
            % repr(policy))


class DatabaseBlockedPolicy(BaseDatabasePolicy):
    """`IDatabasePolicy` that blocks all access to the database."""

    def getStore(self, name, flavor):
        """Raises `DisallowedStore`. No Database access is allowed."""
        raise DisallowedStore(name, flavor)


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


def LaunchpadDatabasePolicyFactory(request):
    """Return the Launchpad IDatabasePolicy for the current appserver state.
    """
    # We need to select a non-load balancing DB policy for some status URLs so
    # it doesn't query the DB for lag information (this page should not
    # hit the database at all). We haven't traversed yet, so we have
    # to sniff the request this way.  Even though PATH_INFO is always
    # present in real requests, we need to tread carefully (``get``) because
    # of test requests in our automated tests.
    if request.get('PATH_INFO') in [u'/+opstats', u'/+haproxy']:
        return DatabaseBlockedPolicy(request)
    elif is_read_only():
        return ReadOnlyLaunchpadDatabasePolicy(request)
    else:
        return LaunchpadDatabasePolicy(request)


class LaunchpadDatabasePolicy(BaseDatabasePolicy):
    """Default database policy for web requests.

    Selects the DEFAULT_FLAVOR based on the request.
    """

    def __init__(self, request):
        # The super constructor is a no-op.
        # pylint: disable-msg=W0231
        self.request = request
        # Detect if this is a read only request or not.
        self.read_only = self.request.method in ['GET', 'HEAD']

    def _hasSession(self):
        "Is there is already a session cookie hanging around?"
        cookie_name = getUtility(IClientIdManager).namespace
        return (
            cookie_name in self.request.cookies or
            self.request.response.getCookie(cookie_name) is not None)

    def install(self):
        """See `IDatabasePolicy`."""
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
                # We don't want to even make a DB query to read the session
                # if we can tell that it is not around.  This can be
                # important for fast and reliable performance for pages like
                # +opstats.
                if self._hasSession():
                    session_data = ISession(self.request)['lp.dbpolicy']
                    last_write = session_data.get('last_write', None)
                else:
                    last_write = None
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
            # We need to further distinguish whether it's safe to write
            # to the session. This will be true if the principal is
            # authenticated or if there is already a session cookie
            # hanging around.
            if not IUnauthenticatedPrincipal.providedBy(
                self.request.principal) or self._hasSession():
                # A non-readonly request has been made. Store this fact
                # in the session. Precision is hard coded at 1 minute
                # (so we don't update the timestamp if it is no more
                # than 1 minute out of date to avoid unnecessary and
                # expensive write operations). Feeds are always read
                # only, and since they run over http, browsers won't
                # send their session key that was set over https, so we
                # don't want to access the session which will overwrite
                # the cookie and log the user out.
                session_data = ISession(self.request)['lp.dbpolicy']
                last_write = session_data.get('last_write', None)
                now = _now()
                if (last_write is None or
                    last_write < now - timedelta(minutes=1)):
                    # set value
                    session_data['last_write'] = now

    def getReplicationLag(self):
        """Return the replication lag on the MAIN_STORE slave.

        Lag to other replication sets is currently ignored.

        :returns: timedelta, or None if this isn't a replicated environment,
        """
        # Support the test suite hook.
        if _test_lag is not None:
            return _test_lag

        # We need to ask our slave what node it is. We can't cache this,
        # as we might have reconnected to a different slave.
        slave_store = self.getStore(MAIN_STORE, SLAVE_FLAVOR)
        slave_node_id = slave_store.execute(
            "SELECT getlocalnodeid()").get_one()[0]
        if slave_node_id is None:
            return None

        # sl_status gives meaningful results only on the origin node.
        master_store = self.getStore(MAIN_STORE, MASTER_FLAVOR)

        # Retrieve the cached lag.
        lag = master_store.execute("""
            SELECT lag + (CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - updated)
            FROM DatabaseReplicationLag WHERE node=%d
            """ % slave_node_id).get_one()
        if lag is None:
            logging.error(
                "No data in DatabaseReplicationLag for node %d"
                % slave_node_id)
            return timedelta(days=999)
        return lag[0]


def WebServiceDatabasePolicyFactory(request):
    """Return the Launchpad IDatabasePolicy for the current appserver state.
    """
    if is_read_only():
        return ReadOnlyLaunchpadDatabasePolicy(request)
    else:
        # If a session cookie was sent with the request, use the
        # standard Launchpad database policy for load balancing to
        # the slave databases. The javascript web service libraries
        # send the session cookie for authenticated users.
        cookie_name = getUtility(IClientIdManager).namespace
        if cookie_name in request.cookies:
            return LaunchpadDatabasePolicy(request)
        # Otherwise, use the master only web service database policy.
        return MasterDatabasePolicy(request)


class ReadOnlyLaunchpadDatabasePolicy(BaseDatabasePolicy):
    """Policy for Launchpad web requests when running in read-only mode.

    Access to all master Stores is blocked.
    """

    def getStore(self, name, flavor):
        """See `IDatabasePolicy`.

        Access to all master Stores is blocked. The default Store is
        the slave.

        Note that we even have to block access to the authdb master
        Store, as it allows access to tables replicated from the
        lpmain replication set. These tables will be locked during
        a lpmain replication set database upgrade.
        """
        if flavor == MASTER_FLAVOR:
            raise ReadOnlyModeDisallowedStore(name, flavor)
        return super(ReadOnlyLaunchpadDatabasePolicy, self).getStore(
            name, SLAVE_FLAVOR)


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
