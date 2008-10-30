# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""PostgreSQL server side session storage for Zope3."""

__metaclass__ = type

import time
import cPickle as pickle
from UserDict import DictMixin
from random import random
from datetime import datetime, timedelta

from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.component import getUtility
from zope.interface import implements
from zope.session.interfaces import (
    ISessionDataContainer, ISessionData, ISessionPkgData, IClientIdManager)

from storm.zope.interfaces import IZStorm
from canonical.launchpad.webapp.publisher import get_current_browser_request


SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES
DAYS = 24 * HOURS


class PGSessionBase:
    store_name = 'session'

    @property
    def store(self):
        return getUtility(IZStorm).get(self.store_name)


class PGSessionDataContainer(PGSessionBase):
    """An ISessionDataContainer that stores data in PostgreSQL

    PostgreSQL Schema:

    CREATE TABLE SessionData (
        client_id     text PRIMARY KEY,
        last_accessed timestamp with time zone
            NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    CREATE INDEX sessiondata_last_accessed_idx ON SessionData(last_accessed);
    CREATE TABLE SessionPkgData (
        client_id  text NOT NULL
            REFERENCES SessionData(client_id) ON DELETE CASCADE,
        product_id text NOT NULL,
        key        text NOT NULL,
        pickle     bytea NOT NULL,
        CONSTRAINT sessiondata_key UNIQUE (client_id, product_id, key)
        );
    """
    implements(ISessionDataContainer)

    timeout = 60 * DAYS
    # If we have a low enough resolution, we can determine active users
    # using the session data.
    resolution = 9 * MINUTES

    session_data_table_name = 'SessionData'
    session_pkg_data_table_name = 'SessionPkgData'

    def __getitem__(self, client_id):
        """See zope.session.interfaces.ISessionDataContainer"""
        self._sweep()
        return PGSessionData(self, client_id)

    def __setitem__(self, client_id, session_data):
        """See zope.session.interfaces.ISessionDataContainer"""
        # The SessionData / SessionPkgData objects know how to store
        # themselves.
        pass

    _last_sweep = datetime.utcnow()
    fuzz = 10 # Our sweeps may occur +- this many seconds to minimize races.

    def _sweep(self):
        interval = timedelta(
                seconds=self.resolution - self.fuzz + 2 * self.fuzz * random()
                )
        now = datetime.utcnow()
        if self._last_sweep + interval > now:
            return
        self._last_sweep = now
        query = """
            DELETE FROM SessionData WHERE last_accessed
                < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '%d seconds'::interval
            """ % self.timeout
        self.store.execute(query, noresult=True)


class PGSessionData(PGSessionBase):
    implements(ISessionData)

    session_data_container = None

    lastAccessTime = None

    _have_ensured_client_id = False

    def __init__(self, session_data_container, client_id):
        self.session_data_container = session_data_container
        self.client_id = client_id
        self.lastAccessTime = time.time()

        # Update the last access time in the db if it is out of date
        table_name = session_data_container.session_data_table_name
        query = """
            UPDATE %s SET last_accessed = CURRENT_TIMESTAMP
            WHERE client_id = ?
                AND last_accessed < CURRENT_TIMESTAMP - '%d seconds'::interval
            """ % (table_name, session_data_container.resolution)
        self.store.execute(query, (client_id,), noresult=True)

    def _ensureClientId(self):
        if self._have_ensured_client_id:
            return
        # We want to make sure the browser cookie and the database both know
        # about our client id. We're doing it lazily to try and keep anonymous
        # users from having a session.
        self.store.execute(
            "SELECT ensure_session_client_id(?)", (self.client_id,),
            noresult=True)
        request = get_current_browser_request()
        if request is not None:
            client_id_manager = getUtility(IClientIdManager)
            if IUnauthenticatedPrincipal.providedBy(request.principal):
                # it would be nice if this could be a monitored, logged
                # message instead of an instant-OOPS.
                assert (client_id_manager.namespace in request.cookies or
                        request.response.getCookie(
                            client_id_manager.namespace) is not None), (
                    'Session data should generally only be stored for '
                    'authenticated users, and for users who have just logged '
                    'out.  If an unauthenticated user has just logged out, '
                    'they should have a session cookie set for ten minutes. '
                    'This should be plenty of time for passing notifications '
                    'about successfully logging out.  Because this assertion '
                    'failed, it means that some code is trying to set '
                    'session data for an unauthenticated user who has been '
                    'logged out for more than ten minutes: something that '
                    'should not happen.  The code setting the session data '
                    'should be reviewed; and failing that, the cookie '
                    'timeout after logout (set in '
                    'canonoical.launchpad.webapp.login) should perhaps be '
                    'increased a bit, if a ten minute fudge factor is not '
                    'enough to handle the vast majority of computers with '
                    'not-very-accurate system clocks.  In an exceptional '
                    'case, the code may set the necessary cookies itself to '
                    'assert that yes, it *should* set the session for an '
                    'unauthenticated user.  See the webapp.login module for '
                    'an example of this, as well.')
            else:
                client_id_manager.setRequestId(request, self.client_id)
        self._have_ensured_client_id = True

    def __getitem__(self, product_id):
        """Return an ISessionPkgData"""
        return PGSessionPkgData(self, product_id)

    def __setitem__(self, product_id, session_pkg_data):
        """See zope.session.interfaces.ISessionData

        This is a noop in the RDBMS implementation.
        """
        pass


class PGSessionPkgData(DictMixin, PGSessionBase):
    implements(ISessionPkgData)

    @property
    def store(self):
        return self.session_data.store

    def __init__(self, session_data, product_id):
        self.session_data = session_data
        self.product_id = product_id
        self.table_name = (
            session_data.session_data_container.session_pkg_data_table_name)
        self._populate()

    _data_cache = None

    def _populate(self):
        self._data_cache = {}
        query = """
            SELECT key, pickle FROM %s WHERE client_id = ?
                AND product_id = ?
            """ % self.table_name
        result = self.store.execute(query, (self.session_data.client_id,
                                   self.product_id))
        for key, pickled_value in result:
            value = pickle.loads(str(pickled_value))
            self._data_cache[key] = value

    def __getitem__(self, key):
        return self._data_cache[key]

    def __setitem__(self, key, value):
        pickled_value =  pickle.dumps(value, pickle.HIGHEST_PROTOCOL)

        self.session_data._ensureClientId()
        self.store.execute("SELECT set_session_pkg_data(?, ?, ?, ?)",
                           (self.session_data.client_id, self.product_id,
                            key, pickled_value), noresult=True)

        # Store the value in the cache too
        self._data_cache[key] = value

    def __delitem__(self, key):
        """Delete an item.

        Note that this will never fail in order to avoid
        race conditions in code using the session machinery
        """
        try:
            del self._data_cache[key]
        except KeyError:
            # Not in the cache, then it won't be in the DB. Or if it is,
            # another process has inserted it and we should keep our grubby
            # fingers out of it.
            return
        query = """
            DELETE FROM %s WHERE client_id = ? AND product_id = ? AND key = ?
            """ % self.table_name
        self.store.execute(query, (self.session_data.client_id,
                                   self.product_id, key), noresult=True)

    def keys(self):
        return self._data_cache.keys()


data_container = PGSessionDataContainer()
