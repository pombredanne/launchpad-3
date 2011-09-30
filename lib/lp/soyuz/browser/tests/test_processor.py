# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for process navigation."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.publisher import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.publication import test_traverse


class TestProcessorNavigation(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_processor_family_url(self):
        family = self.factory.makeProcessorFamily('quantum')
        self.assertEquals(
            '/+processor-families/quantum',
            canonical_url(family, force_local_path=True))

    def test_processor_url(self):
        family = self.factory.makeProcessorFamily('quantum')
        quantum = family.processors[0]
        self.assertEquals(
            '/+processors/quantum',
            canonical_url(quantum, force_local_path=True))

    def test_processor_family_navigation(self):
        family = self.factory.makeProcessorFamily('quantum')
        obj, view, request = test_traverse(
            'http://api.launchpad.dev/devel/+processor-families/quantum')
        self.assertEquals(family, obj)

    def test_processor_navigation(self):
        family = self.factory.makeProcessorFamily('quantum')
        obj, view, request = test_traverse(
            'http://api.launchpad.dev/'
            'devel/+processors/quantum')
        self.assertEquals(family.processors[0], obj)
