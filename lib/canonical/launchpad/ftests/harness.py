# Copyright 2004-2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import unittest
from canonical.ftests.pgsql import PgTestSetup
from canonical.functional import FunctionalTestSetup, FunctionalDocFileSuite

from zope.app import zapi
from zope.component.exceptions import ComponentLookupError
from zope.component.servicenames import Utilities
from zope.component import getService
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from sqlos.interfaces import IConnectionName

from canonical.database.sqlbase import SQLBase
from canonical.lp import initZopeless

from sqlos.connection import connCache

def _disconnect_sqlos():
    try:
        name = zapi.getUtility(IConnectionName).name
        db_adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
        if db_adapter.isConnected():
            # we have to disconnect long enough to drop
            # and recreate the DB
            db_adapter.disconnect()
    except ComponentLookupError, err:
        # configuration not yet loaded, no worries
        pass
    items = list(connCache.items())
    for key, connection in items:
        connection.rollback()
        del connCache[key]

def _reconnect_sqlos():
    db_adapter = None
    db_adapter = None
    name = zapi.getUtility(IConnectionName).name
    db_adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
    if not db_adapter.isConnected():
        db_adapter.connect()
    assert db_adapter.isConnected(), 'Failed to reconnect'
    return db_adapter


class LaunchpadTestSetup(PgTestSetup):
    template = 'launchpad_ftest_template'
    dbname = 'launchpad_ftest' # Needs to match ftesting.zcml

    def setUp(self):
        super(LaunchpadTestSetup, self).setUp()

    def tearDown(self):
        super(LaunchpadTestSetup, self).tearDown()

class LaunchpadZopelessTestSetup(LaunchpadTestSetup):
    txn = None
    def setUp(self):
        super(LaunchpadZopelessTestSetup, self).setUp()
        LaunchpadZopelessTestSetup.txn = initZopeless()

    def tearDown(self):
        LaunchpadZopelessTestSetup.txn.uninstall()
        super(LaunchpadZopelessTestSetup, self).tearDown()

class LaunchpadFunctionalTestSetup(LaunchpadTestSetup):
    def setUp(self):
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        LaunchpadFunctionalTestSetup.sqlos_dbadapter = _reconnect_sqlos()

    def tearDown(self):
        FunctionalTestSetup().tearDown()
        #if self.sqlos_dbadapter.isConnected():
        #    self.sqlos_dbadapter.disconnect()
        _disconnect_sqlos()
        LaunchpadFunctionalTestSetup.sqlos_dbadapter = None
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


