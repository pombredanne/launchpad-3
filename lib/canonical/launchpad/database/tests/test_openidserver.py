# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the OpenID database classes."""

__metaclass__ = type
__all__ = []

import unittest

from storm.zope.interfaces import IZStorm

import transaction

from zope.component import getUtility

from canonical.launchpad.database.openidserver import (
    OpenIDAuthorization, OpenIDAuthorizationSet)
from canonical.launchpad.database.account import Account
from canonical.launchpad.ftests._login import login
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.launchpad.webapp.adapter import StoreSelector
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class OpenIDAuthorizationTestCase(unittest.TestCase):
    """Test for the OpenIDAuthorization database class."""
    layer = DatabaseFunctionalLayer

    def tearDown(self):
        StoreSelector.setGlobalDefaultFlavor(DEFAULT_FLAVOR)

    def test__get_store_should_return_the_auth_master_store(self):
        """We want the OAuthAuthorization check to use the master store,
        because it's modified on GET request which would use the SLAVE_FLAVOR
        by default.
        """
        StoreSelector.setGlobalDefaultFlavor(SLAVE_FLAVOR)
        zstorm = getUtility(IZStorm)
        self.assertEquals(
            'launchpad-%s-%s' % (MAIN_STORE, MASTER_FLAVOR),
            zstorm.get_name(OpenIDAuthorization._get_store()))


class OpenIDAuthorizationSet__with_SlaveStore_TestCase(unittest.TestCase):
    """Test for the OpenIDAuthorizationSet database class."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Mimic the setup when the default store is the SLAVE_FLAVOR."""
        login('no-priv@canonical.com')
        factory = LaunchpadObjectFactory()
        person = factory.makePerson()
        # The person is created on the master flavor, commit and fetch it
        # back from the slave store.
        transaction.commit()
        slave_store = StoreSelector.get(MAIN_STORE, SLAVE_FLAVOR)
        self.account = slave_store.get(Account, person.account.id)

    def test_authorize_works_with_person_loaded_from_the_slave_store(self):
        """OpenIDAuthorization always use the master store.

        But bug #310096 exposed that authorize() failed if the person was
        loaded from the slave.
        """
        authorization_set = OpenIDAuthorizationSet()
        trust_root = 'http://launchpad.dev'
        authorization_set.authorize(self.account, trust_root, None)

        self.failUnless(
            authorization_set.isAuthorized(self.account, trust_root, None),
            'Pre-authorization failed')


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(OpenIDAuthorizationTestCase),
        unittest.makeSuite(OpenIDAuthorizationSet__with_SlaveStore_TestCase),
            ))
