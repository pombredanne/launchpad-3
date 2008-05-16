# Copyright 2004-2005 Canonical Ltd. All rights reserved.
"""
Launchpad functional test helpers.

This file needs to be refactored, moving its functionality into
canonical.testing
"""

__metaclass__ = type

from storm.zope.interfaces import IZStorm
import transaction
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from zope.app.testing.functional import FunctionalTestSetup
from zope.component import getUtility
from zope.component.exceptions import ComponentLookupError

from canonical.config import dbconfig
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
    zstorm = getUtility(IZStorm)
    stores = []
    for store_name in ['main', 'session']:
        if store_name in zstorm._named:
            store = zstorm.get(store_name)
            zstorm.remove(store)
            stores.append(store)
    # If we have any stores, abort the transaction and close them.
    if stores:
        transaction.abort()
        for store in stores:
            store.close()


def _reconnect_sqlos(dbuser=None, database_config_section='launchpad'):
    _disconnect_sqlos()
    dbconfig.setConfigSection(database_config_section)

    main_store = getUtility(IZStorm).get('main')
    assert main_store is not None, 'Failed to reconnect'

    # Confirm the database has the right patchlevel
    confirm_dbrevision(cursor())

    # Confirm that SQLOS is again talking to the database (it connects
    # as soon as SQLBase._connection is accessed
    r = main_store.execute('SELECT count(*) FROM LaunchpadDatabaseRevision')
    assert r.get_one()[0] > 0, 'Storm is not talking to the database'

    session_store = getUtility(IZStorm).get('session')
    assert session_store is not None, 'Failed to reconnect'


class LaunchpadTestSetup(PgTestSetup):
    template = 'launchpad_ftest_template'
    dbname = 'launchpad_ftest' # Needs to match ftesting.zcml
    dbuser = 'launchpad'


class LaunchpadZopelessTestSetup(LaunchpadTestSetup):
    txn = ZopelessTransactionManager
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
        initZopeless(dbname=self.dbname, dbuser=self.dbuser)

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
