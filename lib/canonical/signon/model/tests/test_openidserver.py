# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the OpenID database classes."""

__metaclass__ = type
__all__ = []

import unittest

from storm.zope.interfaces import IZStorm

import transaction

from zope.component import getUtility

from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.dbpolicy import (
    SlaveDatabasePolicy, SSODatabasePolicy)
from canonical.launchpad.webapp.interfaces import (
    AUTH_STORE, IStoreSelector, MASTER_FLAVOR)
from canonical.signon.interfaces.openidserver import (
    IOpenIDAuthorizationSet)
from canonical.signon.model.openidserver import OpenIDAuthorization
from canonical.testing.layers import DatabaseFunctionalLayer


def sso_db_policy(func):
    """Decorator that installs the SSODatabasePolicy."""
    def with_sso_db_policy(*args, **kw):
        store_selector = getUtility(IStoreSelector)
        store_selector.push(SSODatabasePolicy())
        try:
            return func(*args, **kw)
        finally:
            store_selector.pop()
    with_sso_db_policy.__name__ = func.__name__
    return with_sso_db_policy


def slave_db_policy(func):
    """Decorator that installs the SlaveDatabasePolicy."""
    def with_slave_db_policy(*args, **kw):
        store_selector = getUtility(IStoreSelector)
        store_selector.push(SlaveDatabasePolicy())
        try:
            return func(*args, **kw)
        finally:
            store_selector.pop()
    with_slave_db_policy.__name__ = func.__name__
    return with_slave_db_policy


class OpenIDAuthorizationTestCase(unittest.TestCase):
    """Test for the OpenIDAuthorization database class."""
    layer = DatabaseFunctionalLayer

    @slave_db_policy
    def test__get_store_should_return_the_auth_master_store(self):
        """We want the OAuthAuthorization check to use the master store,
        because it's modified on GET request which would use the SLAVE_FLAVOR
        by default.
        """
        zstorm = getUtility(IZStorm)
        self.assertEquals(
            'launchpad-%s-%s' % (AUTH_STORE, MASTER_FLAVOR),
            zstorm.get_name(OpenIDAuthorization._get_store()))


class OpenIDAuthorizationSetTests(TestCaseWithFactory):
    """Test for the OpenIDAuthorizationSet database class."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(OpenIDAuthorizationSetTests, self).setUp(
            user='no-priv@canonical.com')

    @sso_db_policy
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
