# Copyright 2004-2005 Canonical Ltd. All rights reserved.
"""
Launchpad functional test helpers.

This file needs to be refactored, moving its functionality into
canonical.testing
"""

__metaclass__ = type

from zope.app.testing.functional import FunctionalTestSetup

from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.ftests.pgsql import PgTestSetup
from canonical.lp import initZopeless
from canonical.testing import BaseLayer, FunctionalLayer, ZopelessLayer
from canonical.testing.layers import disconnect_stores, reconnect_stores


__all__ = [
    'LaunchpadTestSetup', 'LaunchpadZopelessTestSetup',
    'LaunchpadFunctionalTestSetup',
    ]


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
        assert self.dbuser == 'launchpad', (
            "Non-default user names should probably be using "
            "script layer or zopeless layer.")
        disconnect_stores()
        super(LaunchpadFunctionalTestSetup, self).setUp()
        FunctionalTestSetup().setUp()
        reconnect_stores()

    def tearDown(self):
        self._checkLayerInvariants()
        FunctionalTestSetup().tearDown()
        disconnect_stores()
        super(LaunchpadFunctionalTestSetup, self).tearDown()
