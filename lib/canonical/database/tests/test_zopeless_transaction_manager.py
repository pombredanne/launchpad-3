# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility

from storm.zope.interfaces import IZStorm

from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCase


class TestZopelessTransactionManager(TestCase):
    layer = LaunchpadZopelessLayer

    def test_reset_stores_only_does_so_on_active_stores(self):
        active_stores = [item[0] for item in getUtility(IZStorm).iterstores()]
        self.assertContentEqual(
            ['launchpad-main-master', 'session'], active_stores)
        ZopelessTransactionManager._reset_stores()
        # If any other stores had been reset, they'd be activated and would
        # then be returned by ZStorm.iterstores().
        new_active_stores = [
            item[0] for item in getUtility(IZStorm).iterstores()]
        self.assertContentEqual(active_stores, new_active_stores)
