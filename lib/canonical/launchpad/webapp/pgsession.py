# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""PostgreSQL server side session storage for Zope3."""

__metaclass__ = type

import time
import psycopg
import cPickle as pickle
from UserDict import DictMixin
from random import random
from datetime import datetime, timedelta

from zope.component import getUtility
from zope.interface import implements
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from zope.app.session.interfaces import (
        ISessionDataContainer, ISessionData, ISessionPkgData
        )
from psycopgda.adapter import PG_ENCODING

# XXX: This is only needed for bootstrapping. Final implementation should
# connect via a named PsycopgDA
from canonical.database.sqlbase import cursor

SECONDS = 1
MINUTES = 60 * SECONDS
HOURS = 60 * MINUTES

class PGSessionDataContainer:
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

    timeout = 12 * HOURS
    # If we have a low enough resolution, we can determine active users
    # using the session data.
    resolution = 10 * MINUTES

    session_data_tablename = 'SessionData'
    session_pkg_data_tablename = 'SessionPkgData'
    database_adapter_name = 'session'

    @property
    def cursor(self):
        da = getUtility(IZopeDatabaseAdapter, self.database_adapter_name)
        return da().cursor()

    def __getitem__(self, client_id):
        """See zope.app.session.interfaces.ISessionDataContainer"""
        cursor = self.cursor
        self._sweep(cursor)
        query = "SELECT COUNT(*) FROM %s WHERE client_id = %%(client_id)s" % (
                self.session_data_tablename
                )
        cursor.execute(query.encode(PG_ENCODING), vars())
        if cursor.fetchone()[0] == 0:
            raise KeyError(client_id)
        return PGSessionData(self, client_id)

    def __setitem__(self, client_id, session_data):
        """See zope.app.session.interfaces.ISessionDataContainer"""
        query = "INSERT INTO %s (client_id) VALUES (%%(client_id)s)" % (
                self.session_data_tablename
                )
        client_id = client_id.encode(PG_ENCODING)
        self.cursor.execute(query, vars())

    _last_sweep = datetime.utcnow() - timedelta(days=6)
    fuzz = 10 # Our sweeps may occur +- this many seconds to minimize races.

    def _sweep(self, cursor):
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
        cursor = self.cursor
        cursor.execute(query)


class PGSessionData:
    implements(ISessionData)

    session_data_container = None

    lastAccessTime = None

    def __init__(self, session_data_container, client_id):
        self.session_data_container = session_data_container
        self.client_id = client_id
        self.lastAccessTime = time.time()

        # Update the last access time in the db if it is out of date
        tablename = session_data_container.session_data_tablename
        query = """
            UPDATE %s SET last_accessed = CURRENT_TIMESTAMP
            WHERE client_id = %%s
            AND last_accessed < CURRENT_TIMESTAMP - '%d seconds'::interval
            """ % (tablename, session_data_container.resolution)
        self.cursor.execute(query, [client_id.encode(PG_ENCODING)])

    @property
    def cursor(self):
        return self.session_data_container.cursor

    def __getitem__(self, product_id):
        """Return an ISessionPkgData"""
        return PGSessionPkgData(self, product_id)

    def __setitem__(self, product_id, session_pkg_data):
        """See zope.app.session.interfaces.ISessionData
        
        This is a noop in the RDBMS implementation.
        """
        pass


class PGSessionPkgData(DictMixin):
    implements(ISessionPkgData)

    @property
    def cursor(self):
        return self.session_data.cursor

    def __init__(self, session_data, product_id):
        self.session_data = session_data
        self.product_id = product_id
        self.tablename = \
                session_data.session_data_container.session_pkg_data_tablename

    def __getitem__(self, key):
        query = """
            SELECT pickle FROM %s
            WHERE client_id = %%(client_id)s
                AND product_id = %%(product_id)s AND key = %%(key)s
            """ % self.tablename

        client_id = self.session_data.client_id.encode(PG_ENCODING)
        product_id = self.product_id.encode(PG_ENCODING)
        org_key = key
        key = key.encode(PG_ENCODING)

        cursor = self.cursor
        cursor.execute(query, vars())
        row = cursor.fetchone()
        if row is None:
            raise KeyError(org_key)
        return pickle.loads(row[0])

    def __setitem__(self, key, value):
        pickled_value = psycopg.Binary(
                pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
                )
        cursor = self.cursor

        # Try UPDATE first
        query = """
            UPDATE %s SET pickle = %%(pickled_value)s
            WHERE client_id = %%(client_id)s AND product_id = %%(product_id)s
                AND key = %%(key)s
            """ % self.tablename
        client_id = self.session_data.client_id.encode(PG_ENCODING)
        product_id = self.product_id.encode(PG_ENCODING)
        key = key.encode(PG_ENCODING)
        cursor.execute(query, vars())

        if cursor.rowcount == 1:
            return

        # If no rows where UPDATEd, we need to INSERT
        query = """
            INSERT INTO %s (client_id, product_id, key, pickle) VALUES (
                %%(client_id)s, %%(product_id)s, %%(key)s, %%(pickled_value)s)
            """ % self.tablename
        cursor.execute(query, vars())

    def __delitem__(self, key):
        query = """
            DELETE FROM %s
            WHERE client_id = %%(client_id)s AND product_id = %%(product_id)s
                AND key = %%(key)s
            """ % self.tablename
        client_id = self.session_data.client_id.encode(PG_ENCODING)
        product_id = self.session_data.product_id.encode(PG_ENCODING)
        org_key = key
        key = key.encode(PG_ENCODING)
        cursor = self.cursor
        cursor.execute(query, [
                self.session_data.client_id, self.product_id, key
                ])
        if cursor.rowcount == 0:
            raise KeyError(org_key)

    def keys(self):
        query = """
            SELECT key FROM %s WHERE client_id = %%(client_id)s
                AND product_id = %%(product_id)s
            """ % self.tablename
        client_id = self.session_data.client_id.encode(PG_ENCODING)
        product_id = self.product_id.encode(PG_ENCODING)
        cursor = self.cursor
        cursor.execute(query, vars())
        return [row[0] for row in cursor.fetchall()]


data_container = PGSessionDataContainer()
