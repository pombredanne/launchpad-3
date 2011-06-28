# Copyright 2011 Canonical Ltd.  All rights reserved.

"""Tests for the user requested oops using ++oops++ traversal."""

__metaclass__ = type


from lazr.restful.utils import get_current_browser_request
from zope.location.interfaces import LocationError

from canonical.launchpad.webapp import LaunchpadView
from lp.app.browser.launchpadform import LaunchpadFormView
from canonical.launchpad.webapp.namespace import JsonModelNamespaceView
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS,
    login,
    logout,
    TestCase,
    )


class TestJsonModelView(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)

    def tearDown(self):
        logout()
        TestCase.tearDown(self)

    def test_JsonModelNamespace_traverse_non_LPview(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request
        context = object()
        namespace = JsonModelNamespaceView(context, request)
        self.assertRaises(LocationError,
                          namespace.traverse,"name", None)

    def test_JsonModelNamespace_traverse_LPView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request
        context = object()
        view = LaunchpadView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, view)
        self.assertTrue(hasattr(result, 'index'))

    def test_JsonModelNamespace_traverse_LPFormView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request
        context = object()
        view = LaunchpadFormView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, view)
        self.assertTrue(hasattr(result, 'index'))
