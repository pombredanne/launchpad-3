# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for process navigation."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.services.webapp.publisher import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.publication import test_traverse


class TestProcessorNavigation(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_processor_url(self):
        quantum = self.factory.makeProcessor('quantum')
        self.assertEqual(
            '/+processors/quantum',
            canonical_url(quantum, force_local_path=True))

    def test_processor_navigation(self):
        quantum = self.factory.makeProcessor('quantum')
        obj, view, request = test_traverse(
            'http://api.launchpad.dev/devel/+processors/quantum')
        self.assertEqual(quantum, obj)
