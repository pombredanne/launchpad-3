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
    FeedsDatabasePolicy, MasterDatabasePolicy)
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IDatabasePolicy, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class BaseDatabasePolicyTestCase(unittest.TestCase):
    """Base tests for DatabasePolicy implementation."""
    layer = DatabaseFunctionalLayer

    def tearDown(self):
        StoreSelector.setDefaultFlavor(DEFAULT_FLAVOR)

    def test_afterCall_should_reset_default_flavor(self):
        StoreSelector.setDefaultFlavor(MASTER_FLAVOR)
        self.policy.afterCall()
        self.assertEquals(DEFAULT_FLAVOR, StoreSelector.getDefaultFlavor())


class FeedsDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `FeedsDatabasePolicy`."""

    def setUp(self):
        self.request = (
            LaunchpadTestRequest(SERVER_URL='http://feed.launchpad.dev'))
        setFirstLayer(self.request, FeedsLayer)
        self.policy = getAdapter(self.request, IDatabasePolicy)

    def test_FeedsRequest_dbpolicy_adapter(self):
        self.failUnless(
            isinstance(self.policy, FeedsDatabasePolicy),
            "Expected a FeedsDatabasePolicy, not %s." % self.policy)
        self.failUnless(verifyObject(IDatabasePolicy, self.policy))

    def test_beforeTraverse_should_set_slave_flavor(self):
        """We want to always use the slave flavor for feeds request."""
        self.policy.beforeTraversal()
        self.assertEquals(SLAVE_FLAVOR, StoreSelector.getDefaultFlavor())


class MasterDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `MasterDatabasePolicy`."""

    def setUp(self):
        request = LaunchpadTestRequest(SERVER_URL='http://launchpad.dev')
        self.policy = MasterDatabasePolicy(request)

    def test_MasterPolicy_correctly_implements_IDatabasePolicy(self):
        self.failUnless(verifyObject(IDatabasePolicy, self.policy))

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
        self.assertEquals(MASTER_FLAVOR, StoreSelector.getDefaultFlavor())


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(FeedsDatabasePolicyTestCase),
        unittest.makeSuite(MasterDatabasePolicyTestCase),
            ))
