# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Launchpad's 'view/macro:page' TALES adapter."""

__metaclass__ = type

import os

from zope.component import getMultiAdapter
from zope.location.interfaces import LocationError
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

    def _call_test_tales(self, path):
        test_tales(path, view=self.view)

    def test_base_template(self):
        # Requests on the launchpad.dev vhost use the Launchpad base template.
        adapter = getMultiAdapter([self.view], IPathAdapter, name='macro')
        template_path = os.path.normpath(adapter.base.filename)
        self.assertIn('lp/app/templates', template_path)
        # The base template defines a 'master' macro as the adapter expects.
        self.assertIn('master', adapter.base.macros.keys())

    def test_page(self):
        # A view can be adpated to a page macro object.
        page_macro = test_tales('view/macro:page/main_side', view=self.view)
        self.assertEqual('main_side', self.view.__pagetype__)
        self.assertEqual(('mode', 'html'), page_macro[1])
        source_file = page_macro[3]
        self.assertEqual('setSourceFile', source_file[0])
        self.assertEqual(
            '/templates/base-layout.pt', source_file[1].split('..')[1])

    def test_page_unknown_type(self):
        # An error is raised of the pagetype is not defined.
        self.assertRaisesWithContent(
            LocationError, "'unknown pagetype: not-defined'",
            self._call_test_tales, 'view/macro:page/not-defined')

    def test_pagetype(self):
        # The pagetype is 'unset', until macro:page is called.
        self.assertIs(None, getattr(self.view, '__pagetype__', None))
        self.assertEqual(
            'unset', test_tales('view/macro:pagetype', view=self.view))
        test_tales('view/macro:page/main_side', view=self.view)
        self.assertEqual('main_side', self.view.__pagetype__)
        self.assertEqual(
            'main_side', test_tales('view/macro:pagetype', view=self.view))

    def test_pagehas(self):
        # After the page type is set, the page macro can be queried
        # for what LayoutElements it supports supports.
        test_tales('view/macro:page/main_side', view=self.view)
        self.assertTrue(
            test_tales('view/macro:pagehas/portlets', view=self.view))

    def test_pagehas_unset_pagetype(self):
        # The page macro type must be set before the page macro can be
        # queried for what LayoutElements it supports.
        self.assertRaisesWithContent(
            KeyError, "'unset'",
            self._call_test_tales, 'view/macro:pagehas/fnord')

    def test_pagehas_unknown_attribute(self):
        # An error is raised if the LayoutElement does not exist.
        test_tales('view/macro:page/main_side', view=self.view)
        self.assertRaisesWithContent(
            KeyError, "'fnord'",
            self._call_test_tales, 'view/macro:pagehas/fnord')
