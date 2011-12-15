# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Launchpad's 'view/macro:page' TALES adapter."""

__metaclass__ = type

import os

from zope.component import getMultiAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.launchpad.webapp.publisher import rootObject
from canonical.testing.layers import FunctionalLayer
from lp.testing import (
    TestCase,
    test_tales,
    )
from lp.testing.views import create_view


class TestPageMacroDispatcher(TestCase):

    layer = FunctionalLayer

    def setUp(self):
        super(TestPageMacroDispatcher, self).setUp()
        self.view = create_view(rootObject, name='index.html')

    def test_base_template(self):
        # Requests on the launchpad.dev vhost use the Launchpad base template.
        adapter = getMultiAdapter([self.view], IPathAdapter, name='macro')
        template_path = os.path.normpath(adapter.base.filename)
        self.assertIn('lp/app/templates', template_path)
        # The base template defines a 'master' macro as the adapter expects.
        self.assertIn('master', adapter.base.macros.keys())

    def test_page_type(self):
        page_macro = test_tales('view/macro:page/main_side', view=self.view)
        self.assertEqual(('mode', 'html'), page_macro[1])
        source_file = page_macro[3]
        self.assertEqual('setSourceFile', source_file[0])
        self.assertEqual(
            '/templates/base-layout.pt', source_file[1].split('..')[1])
