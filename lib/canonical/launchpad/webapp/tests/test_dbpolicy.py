# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the DBPolicy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getAdapter
from zope.interface.verify import verifyObject

from canonical.launchpad.layers import FeedsLayer, setFirstLayer
from canonical.launchpad.webapp.adapter import StoreSelector
from canonical.launchpad.webapp.dbpolicy import FeedsDatabasePolicy
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IDatabasePolicy, MASTER_FLAVOR, SLAVE_FLAVOR)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class FeedsDatabasePolicyTestCase(unittest.TestCase):
    """Tests for the FeedsDBPolicy."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        self.request = (
            LaunchpadTestRequest(SERVER_URL='http://feed.launchpad.dev'))
        setFirstLayer(self.request, FeedsLayer)
        self.policy = getAdapter(self.request, IDatabasePolicy)

    def tearDown(self):
        StoreSelector.setDefaultFlavor(DEFAULT_FLAVOR)

    def test_FeedsRequest_dbpolicy_adapter(self):
        self.failUnless(
            isinstance(self.policy, FeedsDatabasePolicy),
            "Expected a feeds-specific DB policy.")
        self.failUnless(verifyObject(IDatabasePolicy, self.policy))

    def test_beforeTraverse_should_set_slave_flavor(self):
        self.policy.beforeTraversal()
        self.assertEquals(SLAVE_FLAVOR, StoreSelector.getDefaultFlavor())

    def test_afterCall_should_reset_default_flavor(self):
        StoreSelector.setDefaultFlavor(MASTER_FLAVOR)
        self.policy.afterCall()
        self.assertEquals(DEFAULT_FLAVOR, StoreSelector.getDefaultFlavor())


def test_suite():
    return unittest.makeSuite(FeedsDatabasePolicyTestCase)
