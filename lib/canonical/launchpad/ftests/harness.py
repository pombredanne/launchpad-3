# Copyright 2004-2005 Canonical Ltd. All rights reserved.
"""
Launchpad functional test helpers.

This file needs to be refactored, moving its functionality into
canonical.testing
"""

__metaclass__ = type

import sqlos
from sqlos.connection import connCache
from sqlos.interfaces import IConnectionName
from zope.rdb.interfaces import IZopeDatabaseAdapter
from zope.app.testing.functional import FunctionalTestSetup
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

from canonical.config import config
from canonical.database.revision import confirm_dbrevision
from canonical.database.sqlbase import (
    cursor, SQLBase, ZopelessTransactionManager)
from canonical.ftests.pgsql import PgTestSetup
from canonical.launchpad.webapp.interfaces import ILaunchpadDatabaseAdapter
from canonical.lp import initZopeless
from canonical.testing import BaseLayer, FunctionalLayer, ZopelessLayer


__all__ = [
    'LaunchpadTestSetup', 'LaunchpadZopelessTestSetup',
    'LaunchpadFunctionalTestSetup',
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
    if dbuser is None:
        dbuser = config[database_config_section].dbuser
    name = getUtility(IConnectionName).name
    da = getUtility(IZopeDatabaseAdapter, name)
    da.switchUser(dbuser)

    # Confirm that the database adapter *really is* connected.
    assert da.isConnected(), 'Failed to reconnect'

    # Confirm that the SQLOS connection cache has been emptied, so access
    # to SQLBase._connection will get a fresh Tranaction
    assert len(connCache.keys()) == 0, (
        'SQLOS appears to have kept connections')

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
    def _checkLayerInvariants(self):
        assert FunctionalLayer.isSetUp or ZopelessLayer.isSetUp, """
                FunctionalTestSetup invoked at an inappropriate time.
                May only be invoked in the FunctionalLayer or ZopelessLayer
                """

    def setUp(self, dbuser=None):
        self._checkLayerInvariants()
        if dbuser is not None:
            self.dbuser = dbuser
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        _reconnect_sqlos(self.dbuser)

    def tearDown(self):
        self._checkLayerInvariants()
        FunctionalTestSetup().tearDown()
        _disconnect_sqlos()
        super(LaunchpadFunctionalTestSetup, self).tearDown()
