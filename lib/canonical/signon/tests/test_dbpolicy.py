# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the SSODBPolicy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getUtility

from lp.testing import TestCase

from canonical.config import config
from canonical.launchpad.interfaces import IMasterStore, ISlaveStore
from canonical.launchpad.layers import setFirstLayer
from canonical.signon.layers import IdLayer, OpenIDLayer
from canonical.signon.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import (
    ALL_STORES, AUTH_STORE, DEFAULT_FLAVOR, DisallowedStore, IDatabasePolicy,
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import FunctionalLayer
from canonical.launchpad.webapp.tests.test_dbpolicy import (
  BaseDatabasePolicyTestCase)


class SSODatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Test the `SSODatabasePolicy`."""

    def setUp(self):
        self.policy = SSODatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_defaults(self):
        # Test that the default store are properly set by the policy.
        self.assertCorrectlyProvides(
            getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR),
            ISlaveStore)
        self.assertCorrectlyProvides(
            getUtility(IStoreSelector).get(AUTH_STORE, DEFAULT_FLAVOR),
            IMasterStore)

    def test_disallowed(self):
        # Test that the slave flavor is disallowed on the Auth store and
        # that the master flavor is disallowed on the other stores.
        for store in ALL_STORES:
            if store == AUTH_STORE:
                disallowed_flavor = SLAVE_FLAVOR
            else:
                disallowed_flavor = MASTER_FLAVOR
            self.failUnlessRaises(
                DisallowedStore,
                getUtility(IStoreSelector).get, store, disallowed_flavor)

    def test_dbusers(self):
        # Test that the correct dbuser is used for each store.
        store_selector = getUtility(IStoreSelector)
        for store in ALL_STORES:
            if store == AUTH_STORE:
                user = 'sso_auth'
            else:
                user = 'sso_main'
            self.failUnlessEqual(
                user,
                self.getDBUser(store_selector.get(store, DEFAULT_FLAVOR)))


class SSOLayerDatabaseRegistrationTestCase(TestCase):
    """Test the ZCML registration of the SSODatabasePolicy policy."""
    layer = FunctionalLayer

    def test_OpenIDLayer_uses_SSODatabasePolicy(self):
        # Test that the OpenIDLayer uses the SSODatabasePolicy.
        request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.dev/+openid')
        setFirstLayer(request, OpenIDLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, SSODatabasePolicy)

    def test_IdLayer_uses_SSODatabasePolicy(self):
        # Test that the IdLayer uses the SSODatabasePolicy.
        request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.dev/+openid')
        setFirstLayer(request, IdLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, SSODatabasePolicy)

    def test_read_only_mode_IdLayer_uses_SSODatabasePolicy(self):
        # Test that the OpenIDLayer in read-only mode uses the 
        # SSODatabasePolicy.
        config.push('read_only', """
            [launchpad]
            read_only: True""")
        try:
            request = LaunchpadTestRequest(
                SERVER_URL='http://openid.launchpad.dev/+openid')
            setFirstLayer(request, IdLayer)
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, SSODatabasePolicy)
        finally:
            config.pop('read_only')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
