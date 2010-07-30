# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for browsing the root of the vostok skin."""

__metaclass__ = type

import unittest

from zope.app.publisher.browser import getDefaultViewName

from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase
from lp.testing.views import create_initialized_view
from lp.vostok.browser.root import VostokRootView
from lp.vostok.browser.tests.request import VostokTestRequest
from lp.vostok.publisher import VostokLayer, VostokRoot


class TestBrowseRoot(TestCase):

    layer = FunctionalLayer

    def test_root_default_view_name(self):
        # The default view for the vostok root object is called "+index".
        view_name = getDefaultViewName(VostokRoot(), VostokTestRequest())
        self.assertEquals('+index', view_name)

    def test_root_index_view(self):
        # VostokRootView is registered as the view for the VostokRoot object.
        view = create_initialized_view(
            VostokRoot(), name='+index', layer=VostokLayer)
        self.assertIsInstance(view, VostokRootView)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
