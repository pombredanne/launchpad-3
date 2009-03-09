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
from canonical.launchpad.interfaces.openidserver import (
    IOpenIDAuthorizationSet)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.adapter import StoreSelector
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


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


class OpenIDAuthorizationSetTests(TestCaseWithFactory):
    """Test for the OpenIDAuthorizationSet database class."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(OpenIDAuthorizationSetTests, self).setUp(
            user='no-priv@canonical.com')

    def test_getByAccount(self):
        """Test behaviour of the getByAccount() method."""
        account = self.factory.makeAccount("Test Account")

        # Create two authorizations, committing the transaction so
        # that we get different creation dates.
        auth_set = getUtility(IOpenIDAuthorizationSet)
        auth_set.authorize(account, "http://example.com", None)
        transaction.commit()
        auth_set.authorize(account, "http://example2.com", None)

        result = auth_set.getByAccount(account)
        self.assertEqual(result.count(), 2)
        [authorization1, authorization2] = result
        self.assertEqual(authorization1.trust_root, "http://example2.com")
        self.assertEqual(authorization2.trust_root, "http://example.com")


class OpenIDAuthorizationSet__with_SlaveStore_TestCase(TestCaseWithFactory):
    """Test for the OpenIDAuthorizationSet database class."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Mimic the setup when the default store is the SLAVE_FLAVOR."""
        super(OpenIDAuthorizationSet__with_SlaveStore_TestCase, self).setUp(
            user='no-priv@canonical.com')
        person = self.factory.makePerson()
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
    return unittest.TestLoader().loadTestsFromName(__name__)
