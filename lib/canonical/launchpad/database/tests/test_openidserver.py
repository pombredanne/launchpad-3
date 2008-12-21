# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the OpenID database classes."""

__metaclass__ = type
__all__ = []

import unittest

from storm.zope.interfaces import IZStorm

from zope.component import getUtility

from canonical.launchpad.database.openidserver import OpenIDAuthorization
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.adapter import StoreSelector
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)


class OpenIDAuthorizationTestCase(unittest.TestCase):
    """Test for the OpenIDAuthorization database class."""
    layer = DatabaseFunctionalLayer

    def tearDown(self):
        StoreSelector.setDefaultFlavor(DEFAULT_FLAVOR)

    def test__get_store_should_return_the_auth_master_store(self):
        """We want the OAuthAuthorization check to use the master store,
        because it's modified on GET request which would use the SLAVE_FLAVOR
        by default.
        """
        StoreSelector.setDefaultFlavor(SLAVE_FLAVOR)
        zstorm = getUtility(IZStorm)
        self.assertEquals(
            '%s-%s' % (MAIN_STORE, MASTER_FLAVOR),
            zstorm.get_name(OpenIDAuthorization._get_store()))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(OpenIDAuthorizationTestCase),
            ))
