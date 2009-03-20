# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the DBPolicy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getAdapter, getGlobalSiteManager, provideUtility
from zope.interface.verify import verifyObject
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest

from canonical.launchpad.layers import (
    FeedsLayer, setFirstLayer, WebServiceLayer)
from canonical.launchpad.webapp.adapter import StoreSelector
from canonical.launchpad.webapp.dbpolicy import (
    SlaveDatabasePolicy, MasterDatabasePolicy)
from canonical.launchpad.webapp.interfaces import (
    ALL_STORES, DEFAULT_FLAVOR, IDatabasePolicy, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer

from canonical.launchpad.webapp.tests import DummyConfigurationTestCase


class BaseDatabasePolicyTestCase(unittest.TestCase):
    """Base tests for DatabasePolicy implementation."""
    layer = DatabaseFunctionalLayer

    def tearDown(self):
        for store in ALL_STORES:
            StoreSelector.setDefaultFlavor(store, DEFAULT_FLAVOR)

    def test_correctly_implements_IDatabasePolicy(self):
        self.failUnless(verifyObject(IDatabasePolicy, self.policy))

    def test_afterCall_should_reset_default_flavor(self):
        for store in ALL_STORES:
            default_flavor = StoreSelector.getDefaultFlavor(store)
            StoreSelector.setDefaultFlavor(store, MASTER_FLAVOR)
            self.policy.afterCall()
            self.assertEquals(
                    default_flavor, StoreSelector.getDefaultFlavor(store))


class SlaveDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def setUp(self):
        self.policy = SlaveDatabasePolicy(
            LaunchpadTestRequest(SERVER_URL='http://launchpad.dev'))

    def test_FeedsLayer_uses_SlaveDatabasePolicy(self):
        """FeedsRequest should use the SlaveDatabasePolicy since they
        are read-only in nature. Also we don't want to send session cookies 
        over them.
        """
        request = LaunchpadTestRequest(
            SERVER_URL='http://feeds.launchpad.dev')
        setFirstLayer(request, FeedsLayer)
        policy = getAdapter(request, IDatabasePolicy)
        self.failUnless(
            isinstance(policy, SlaveDatabasePolicy),
            "Expected SlaveDatabasePolicy, not %s." % policy)

    def test_beforeTraverse_should_set_slave_flavor(self):
        self.policy.beforeTraversal()
        for store in ALL_STORES:
            self.assertEquals(
                    SLAVE_FLAVOR, StoreSelector.getDefaultFlavor(store))


class MasterDatabasePolicyTestCase(
    BaseDatabasePolicyTestCase, DummyConfigurationTestCase):
    """Tests for the `MasterDatabasePolicy`."""

    def setUp(self):
        super(MasterDatabasePolicyTestCase, self).setUp()
        self.policy = MasterDatabasePolicy(
           LaunchpadTestRequest(SERVER_URL='http://launchpad.dev'))

    def test_XMLRPCRequest_uses_MasterPolicy(self):
        """XMLRPC should always use the master flavor, since they always
        use POST and do not support session cookies.
        """
        request = LaunchpadTestRequest(
            SERVER_URL='http://xmlrpc-private.launchpad.dev')
        setFirstLayer(request, IXMLRPCRequest)
        policy = getAdapter(request, IDatabasePolicy)
        self.failUnless(
            isinstance(policy, MasterDatabasePolicy),
            "Expected MasterDatabasePolicy, not %s." % policy)

    def test_WebServiceRequest_uses_MasterPolicy(self):
        """WebService requests should always use the master flavor, since
        it's likely that clients won't support cookies and thus mixing read
        and write requests will result in incoherent views of the data.
        """
        server_url = ('http://api.launchpad.dev/'
                      + self.config.service_version_uri_prefix)
        request = LaunchpadTestRequest(SERVER_URL=server_url)
        setFirstLayer(request, WebServiceLayer)
        policy = getAdapter(request, IDatabasePolicy)
        self.failUnless(
            isinstance(policy, MasterDatabasePolicy),
            "Expected MasterDatabasePolicy, not %s." % policy)

    def test_beforeTraverse_should_set_master_flavor(self):
        self.policy.beforeTraversal()
        for store in ALL_STORES:
            self.assertEquals(
                    MASTER_FLAVOR, StoreSelector.getDefaultFlavor(store))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(SlaveDatabasePolicyTestCase),
        unittest.makeSuite(MasterDatabasePolicyTestCase),
            ))
