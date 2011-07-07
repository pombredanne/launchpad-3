# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the builders webservice ."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from lp.testing import (
    logout,
    TestCaseWithFactory,
    )


class TestBuildersCollection(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBuildersCollection, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()
        # webservice doesn't like dangling interactions.
        logout()

    def test_getBuildQueueSizes(self):
        results = self.webservice.named_get(
            '/builders', 'getBuildQueueSizes', api_version='devel')
        self.assertEquals(
            ['nonvirt', 'virt'], sorted(results.jsonBody().keys()))


