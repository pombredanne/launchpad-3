# Copyright 2004-2005 Canonical Ltd. All rights reserved.
"""
Launchpad functional test helpers.

This file needs to be refactored, moving its functionality into
canonical.testing
"""

__metaclass__ = type

import unittest
from zope.component import getUtility
from zope.component.exceptions import ComponentLookupError
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from sqlos.interfaces import IConnectionName

from canonical.testing import (
        BaseLayer, LibrarianLayer, FunctionalLayer, LaunchpadZopelessLayer,
        )
from canonical.ftests.pgsql import PgTestSetup
from canonical.functional import FunctionalTestSetup
from canonical.config import dbconfig
from canonical.database.revision import confirm_dbrevision
from canonical.database.sqlbase import (
        cursor, SQLBase, ZopelessTransactionManager,
        )
from canonical.lp import initZopeless
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.launchpad.webapp.interfaces import ILaunchpadDatabaseAdapter

import sqlos
from sqlos.connection import connCache

__all__ = [
    'LaunchpadTestSetup', 'LaunchpadTestCase',
    'LaunchpadZopelessTestSetup',
    'LaunchpadFunctionalTestSetup', 'LaunchpadFunctionalTestCase',
    '_disconnect_sqlos', '_reconnect_sqlos'
    ]

def _disconnect_sqlos():
    try:
        name = getUtility(IConnectionName).name
        da = ILaunchpadDatabaseAdapter(getUtility(IZopeDatabaseAdapter, name))
        # we have to disconnect long enough to drop
        # and recreate the DB
        da.disconnect()
        assert da._v_connection is None
    except ComponentLookupError:
        # configuration not yet loaded, no worries
        pass

    try:
        da = getUtility(IZopeDatabaseAdapter, 'session')
        da.disconnect()
        assert da._v_connection is None
    except ComponentLookupError:
        # configuration not yet loaded, no worries
        pass

    items = list(connCache.items())
    for key, connection in items:
        connection.rollback()
        del connCache[key]
    sqlos.connection.connCache.clear()

def _reconnect_sqlos(dbuser=None, database_config_section='launchpad'):
    _disconnect_sqlos()
    dbconfig.setConfigSection(database_config_section)
    name = getUtility(IConnectionName).name
    da = getUtility(IZopeDatabaseAdapter, name)
    da.switchUser(dbuser)

    # Confirm that the database adapter *really is* connected.
    assert da.isConnected(), 'Failed to reconnect'

    # Confirm that the SQLOS connection cache has been emptied, so access
    # to SQLBase._connection will get a fresh Tranaction
    assert len(connCache.keys()) == 0, 'SQLOS appears to have kept connections'

    # Confirm the database has the right patchlevel
    confirm_dbrevision(cursor())

    # Confirm that SQLOS is again talking to the database (it connects
    # as soon as SQLBase._connection is accessed
    r = SQLBase._connection.queryAll(
            'SELECT count(*) FROM LaunchpadDatabaseRevision'
            )
    assert r[0][0] > 0, 'SQLOS is not talking to the database'

    da = getUtility(IZopeDatabaseAdapter, 'session')
    da.connect()
    assert da.isConnected(), 'Failed to reconnect'


class LaunchpadTestSetup(PgTestSetup):
    template = 'launchpad_ftest_template'
    dbname = 'launchpad_ftest' # Needs to match ftesting.zcml
    dbuser = 'launchpad'


class LaunchpadZopelessTestSetup(LaunchpadTestSetup):
    txn = None
    def setUp(self, dbuser=None):
        assert ZopelessTransactionManager._installed is None, \
                'Last test using Zopeless failed to tearDown correctly'
        super(LaunchpadZopelessTestSetup, self).setUp()
        if self.host is not None:
            raise NotImplementedError('host not supported yet')
        if self.port is not None:
            raise NotImplementedError('port not supported yet')
        if dbuser is not None:
            self.dbuser = dbuser
        LaunchpadZopelessTestSetup.txn = initZopeless(
                dbname=self.dbname, dbuser=self.dbuser
                )

    def tearDown(self):
        LaunchpadZopelessTestSetup.txn.uninstall()
        assert ZopelessTransactionManager._installed is None, \
                'Failed to tearDown Zopeless correctly'

        # Tests using Layers don't want the database torn down here, as the
        # Layer does it for us. However, this helper is currently also in
        # use by the importd tests that do not use layers, so we need to cope.
        if not BaseLayer.isSetUp:
            super(LaunchpadZopelessTestSetup, self).tearDown()


class LaunchpadFunctionalTestSetup(LaunchpadTestSetup):
    def setUp(self, dbuser=None):
        if dbuser is not None:
            self.dbuser = dbuser
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        _reconnect_sqlos(self.dbuser)

    def tearDown(self):
        FunctionalTestSetup().tearDown()
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).tearDown()


class LaunchpadTestCase(unittest.TestCase):
    dbuser = LaunchpadTestSetup.dbuser
    dbname = LaunchpadTestSetup.dbname
    template = LaunchpadTestSetup.template
    # XXX StuartBishop 2006-07-13: Should be Launchpad, but we need to
    # specify how to change the db user to connect as.
    layer = LibrarianLayer

    def setUp(self):
        self._setup = LaunchpadTestSetup()
        self._setup.dbuser = self.dbuser
        self._setup.dbname = self.dbname
        self._setup.template = self.template

        self._setup.setUp()

    def tearDown(self):
        self._setup.tearDown()

    def connect(self):
        return self._setup.connect()


class LaunchpadFunctionalTestCase(unittest.TestCase):
    # XXX StuartBishop 2006-07-13: Should be LaunchpadFunctional, but we
    # first need to implement a way of specifying the dbuser to connect as.
    layer = FunctionalLayer
    dbuser = None
    def login(self, user=None):
        """Login the current zope request as user.

        If no user is provided, ANONYMOUS is used.
        """
        if user is None:
            user = ANONYMOUS
        login(user)
        self.__logged_in = True

    def setUp(self, dbuser=None):
        if dbuser is not None:
            self.dbuser = dbuser
        unittest.TestCase.setUp(self)
        LaunchpadFunctionalTestSetup(dbuser=self.dbuser).setUp()
        self.__logged_in = False

    def tearDown(self):
        if self.__logged_in:
            logout()
            self.__logged_in = False
        LaunchpadFunctionalTestSetup(dbuser=self.dbuser).tearDown()
        unittest.TestCase.tearDown(self)

    def connect(self):
        return LaunchpadFunctionalTestSetup(dbuser=self.dbuser).connect()


class LaunchpadZopelessTestCase(unittest.TestCase):
    layer = LaunchpadZopelessLayer

