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

    def test_getBuildQueueSizes(self):
        logout()
        results = self.webservice.named_get(
            '/builders', 'getBuildQueueSizes', api_version='devel')
        self.assertEquals(
            ['nonvirt', 'virt'], sorted(results.jsonBody().keys()))

    def test_getBuildersForQueue(self):
        g1 = self.factory.makeProcessorFamily('g1').processors[0]
        quantum = self.factory.makeProcessorFamily('quantum').processors[0]
        self.factory.makeBuilder(
            processor=quantum, name='quantum_builder1')
        self.factory.makeBuilder(
            processor=quantum, name='quantum_builder2')
        self.factory.makeBuilder(
            processor=quantum, name='quantum_builder3', virtualized=False)
        self.factory.makeBuilder(
            processor=g1, name='g1_builder', virtualized=False)

        logout()
        results = self.webservice.named_get(
            '/builders', 'getBuildersForQueue',
            processor=api_url(quantum), virtualized=True,
            api_version='devel').jsonBody()
        self.assertEquals(
            ['quantum_builder1', 'quantum_builder2'],
            sorted(builder['name'] for builder in results['entries']))


class TestBuilderEntry(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBuilderEntry, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_exports_processor(self):
        processor_family = self.factory.makeProcessorFamily('s1')
        builder = self.factory.makeBuilder(
            processor=processor_family.processors[0])

        logout()
        entry = self.webservice.get(
            api_url(builder), api_version='devel').jsonBody()
        self.assertEndsWith(entry['processor_link'], '/+processors/s1')
