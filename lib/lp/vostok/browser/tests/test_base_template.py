# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the vostok 'view/macro:page' TALES adapter."""

__metaclass__ = type

from zope.component import getMultiAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.testing.layers import FunctionalLayer
from lp.testing import TestCase
from lp.vostok.browser.tests.request import VostokTestRequest
from lp.vostok.publisher import VostokRoot


class TestPageMacroDispatcher(TestCase):

    layer = FunctionalLayer

    def test_base_template(self):
        # For requests on the vostok vhost (i.e. IVostokLayer requests), the
        # base template used is the vostok one.
        root_view = getMultiAdapter(
            (VostokRoot(), VostokTestRequest()), name='+index')
        adapter = getMultiAdapter([root_view], IPathAdapter, name='macro')
        self.assertIn('lp/vostok', adapter.base.filename)
        # The vostok base template defines a 'master' macro as the adapter
        # expects.
        self.assertIn('master', adapter.base.macros.keys())
