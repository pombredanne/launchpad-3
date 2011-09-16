# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import warnings

from storm.zope.interfaces import IZStorm
from zope.component import getUtility

from canonical.database.sqlbase import (
    alreadyInstalledMsg,
    ZopelessTransactionManager,
    )
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
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


class TestInitZopeless(TestCase):

    layer = ZopelessDatabaseLayer

    def test_initZopelessTwice(self):
        # Hook the warnings module, so we can verify that we get the expected
        # warning.  The warnings module has two key functions, warn and
        # warn_explicit, the first calling the second. You might, therefore,
        # think that we should hook the second, to catch all warnings in one
        # place.  However, from Python 2.6, both of these are replaced with
        # entries into a C extension if available, and the C implementation of
        # the first will not call a monkeypatched Python implementation of the
        # second.  Therefore, we hook warn, as is the one actually called by
        # the particular code we are interested in testing.
        original_warn = warnings.warn
        warnings.warn = self.warn_hooked
        self.warned = False
        try:
            # Calling initZopeless with the same arguments twice should return
            # the exact same object twice, but also emit a warning.
            try:
                tm1 = ZopelessTransactionManager.initZopeless(
                    dbuser='launchpad')
                tm2 = ZopelessTransactionManager.initZopeless(
                    dbuser='launchpad')
                self.failUnless(tm1 is tm2)
                self.failUnless(self.warned)
            finally:
                tm1.uninstall()
        finally:
            # Put the warnings module back the way we found it.
            warnings.warn = original_warn

    def warn_hooked(self, message, category=None, stacklevel=1):
        self.failUnlessEqual(alreadyInstalledMsg, str(message))
        self.warned = True
