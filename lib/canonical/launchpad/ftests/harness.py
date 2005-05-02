# Copyright 2004-2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from canonical.ftests.pgsql import PgTestSetup, ConnectionWrapper
from canonical.functional import FunctionalTestSetup, FunctionalDocFileSuite

from zope.app import zapi
from zope.component.exceptions import ComponentLookupError
from zope.component.servicenames import Utilities
from zope.component import getService
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from sqlos.interfaces import IConnectionName

from canonical.database.sqlbase import SQLBase
from canonical.lp import initZopeless

import sqlos
from sqlos.connection import connCache

def _disconnect_sqlos():
    try:
        name = zapi.getUtility(IConnectionName).name
        db_adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
        # we have to disconnect long enough to drop
        # and recreate the DB
        db_adapter.disconnect()
        assert db_adapter._v_connection is None
    except ComponentLookupError, err:
        # configuration not yet loaded, no worries
        pass
    items = list(connCache.items())
    for key, connection in items:
        connection.rollback()
        del connCache[key]
    sqlos.connection.connCache = {}

def _reconnect_sqlos():
    _disconnect_sqlos()
    db_adapter = None
    name = zapi.getUtility(IConnectionName).name
    db_adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
    db_adapter.connect()

    # Confirm that the database adapter *really is* connected and connected
    # to the right database
    assert db_adapter.isConnected(), 'Failed to reconnect'
    cur = db_adapter._v_connection.cursor()
    cur.execute('SELECT count(*) FROM person')
    assert cur.fetchone()[0] > 0, 'Sample data not loaded!'

    # Confirm that the SQLOS connection cache has been emptied, so access
    # to SQLBase._connection will get a fresh Tranaction
    assert len(connCache.keys()) == 0, 'SQLOS appears to have kept connections'

    # Confirm that SQLOS is again talking to the database (it connects
    # as soon as SQLBase._connection is accessed
    r = SQLBase._connection.queryAll('SELECT count(*) FROM person')
    assert r[0][0] > 0, 'SQLOS is not talking to the database'


class LaunchpadTestSetup(PgTestSetup):
    template = 'launchpad_ftest_template'
    dbname = 'launchpad_ftest' # Needs to match ftesting.zcml
    dbuser = 'launchpad'
    dbhost = 'localhost'


class LaunchpadZopelessTestSetup(LaunchpadTestSetup):
    txn = None
    def setUp(self):
        super(LaunchpadZopelessTestSetup, self).setUp()
        LaunchpadZopelessTestSetup.txn = initZopeless(
                dbname=self.dbname, dbuser=self.dbuser
                )

    def tearDown(self):
        LaunchpadZopelessTestSetup.txn.uninstall()
        super(LaunchpadZopelessTestSetup, self).tearDown()


class LaunchpadFunctionalTestSetup(LaunchpadTestSetup):
    def setUp(self):
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        _reconnect_sqlos()
        
    def tearDown(self):
        FunctionalTestSetup().tearDown()
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).tearDown()


class LaunchpadTestCase(unittest.TestCase):
    def setUp(self):
        LaunchpadTestSetup().setUp()

    def tearDown(self):
        LaunchpadTestSetup().tearDown()

    def connect(self):
        return LaunchpadTestSetup().connect()


class LaunchpadFunctionalTestCase(unittest.TestCase):
    def setUp(self):
        LaunchpadFunctionalTestSetup().setUp()
        self.zodb_db = FunctionalTestSetup().db

    def tearDown(self):
        LaunchpadFunctionalTestSetup().tearDown()

    def connect(self):
        return LaunchpadFunctionalTestSetup().connect()


