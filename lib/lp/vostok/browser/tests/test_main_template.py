# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the vostok 'main_template'."""

__metaclass__ = type

import unittest

from zope.component import getMultiAdapter

from canonical.testing.layers import FunctionalLayer

from lp.testing import TestCase
from lp.vostok.browser.tests.request import VostokTestRequest


class TestMainTemplate(TestCase):
    """Tests for our main template."""

    layer = FunctionalLayer

    def test_main_template_defines_master_macro(self):
        # The main template, which is registered as a view for any object at
        # all when in the VostokLayer, defines a 'master' macro.
        adapter = getMultiAdapter(
            (None, VostokTestRequest()), name='main_template')
        self.assertEqual(['master'], adapter.index.macros.keys())
        self.assertIn('lp/vostok', adapter.index.filename)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
