# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the DBPolicy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getAdapter
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


class ImplicitDatabasePolicyTestCase(unittest.TestCase):
    """Tests for when there is no policy installed."""
    layer = DatabaseFunctionalLayer

    def test_defaults(self):
        main_store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

        self.failUnless(verifyObject(IMasterStore, main_store))

        auth_store = geteUtility(IStoreSelector).get(
            AUTH_STORE, DEFAULT_FLAVOR)
        self.failUnless(verifyObject(IMasterStore, auth_store))


class BaseDatabasePolicyTestCase(ImplicitDatabasePolicyTestCase):
    """Base tests for DatabasePolicy implementation."""

    def setUp(self):
        self.policy = BaseDatabasePolicy()
        getUtility(IStoreSelector).push(self.policy)

    def tearDown(self):
        getUtility(IStoreSelector).pop()

    def test_correctly_implements_IDatabasePolicy(self):
        self.failUnless(verifyObject(IDatabasePolicy, self.policy))


class SlaveDatabasePolicyTestCase(unittest.TestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def test_FeedsLayer_uses_SlaveDatabasePolicy(self):
        """FeedsRequest should use the SlaveDatabasePolicy since they
        are read-only in nature. Also we don't want to send session cookies 
        over them.
        """
        request = LaunchpadTestRequest(
            SERVER_URL='http://feeds.launchpad.dev')
        setFirstLayer(request, FeedsLayer)
        policy = IDatabasePolicy(request)
        self.failUnless(
            isinstance(policy, SlaveDatabasePolicy),
            "Expected SlaveDatabasePolicy, not %s." % policy)

    def test_beforeTraverse_should_set_slave_flavor(self):
        self.policy.beforeTraversal()
        for store in ALL_STORES:
            self.assertEquals(
                    SLAVE_FLAVOR, StoreSelector.getDefaultFlavor(store))


class MasterDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `MasterDatabasePolicy`."""

    def setUp(self):
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
        request = LaunchpadTestRequest(
            SERVER_URL='http://api.launchpad.dev/beta')
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
