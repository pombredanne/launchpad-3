# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the builders webservice ."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from lp.testing import (
    api_url,
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


class TestBuilderEntry(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBuilderEntry, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_exports_processor(self):
        processor_family = self.factory.makeProcessorFamily(
            'supersecret', default_processor_name='s1')
        builder = self.factory.makeBuilder(
            processor=processor_family.processors[0])

        logout()
        entry = self.webservice.get(
            api_url(builder), api_version='devel').jsonBody()
        self.assertEndsWith(
            entry['processor_link'],
            '/+processor-families/supersecret/s1')
