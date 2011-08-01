# Copyright 2011 Canonical Ltd.  All rights reserved.

"""Tests for the user requested oops using ++oops++ traversal."""

__metaclass__ = type


from lazr.restful.interfaces import IJSONRequestCache
from lazr.restful.utils import get_current_browser_request
from simplejson import loads
from testtools.matchers import KeysEqual
from zope.configuration import xmlconfig

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.namespace import JsonModelNamespaceView
import canonical.launchpad.webapp.tests
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.launchpadform import LaunchpadFormView
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    logout,
    TestCaseWithFactory,
    )


class FakeView:
    """A view object that just has a fake context and request."""
    def __init__(self):
        self.context = object()
        self.request = object()


class TestJsonModelNamespace(TestCaseWithFactory):
    """Test that traversal to ++model++ returns a namespace."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ANONYMOUS)

    def tearDown(self):
        logout()
        TestCaseWithFactory.tearDown(self)

    def test_JsonModelNamespace_traverse_non_LPview(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request()
        context = object()
        view = FakeView()
        namespace = JsonModelNamespaceView(context, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)

    def test_JsonModelNamespace_traverse_LPView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request()
        context = object()
        view = LaunchpadView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)

    def test_JsonModelNamespace_traverse_LPFormView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request()
        context = object()
        view = LaunchpadFormView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)


class BaseProductModelTestView(LaunchpadView):
    def initialize(self):
        # Ensure initialize does not put anything in the cache.
        pass


class TestJsonModelView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ANONYMOUS)
        self.product = self.factory.makeProduct(name="test-product")
        self.url = canonical_url(self.product) + '/+modeltest/++model++'

    def tearDown(self):
        logout()
        TestCaseWithFactory.tearDown(self)

    def configZCML(self):
        # Register the ZCML for our test view.  Note the view class must be
        # registered first.
        xmlconfig.string("""
          <configure
              xmlns:browser="http://namespaces.zope.org/browser">
              <include package="canonical.launchpad.webapp"
                  file="meta.zcml" />
              <include package="zope.app.zcmlfiles" file="meta.zcml" />
              <browser:page
                name="+modeltest"
                for="lp.registry.interfaces.product.IProduct"
                class="canonical.launchpad.webapp.tests.ProductModelTestView"
                permission="zope.Public"
                />
          </configure>""")

    def test_JsonModel_default_cache(self):
        # If nothing is added to the class by the view, the cache will only
        # have the context.
        class ProductModelTestView(BaseProductModelTestView):
            pass
        canonical.launchpad.webapp.tests.ProductModelTestView = \
            ProductModelTestView
        self.configZCML()
        browser = self.getUserBrowser(self.url)
        cache = loads(browser.contents)
        self.assertEqual(['context'], cache.keys())

    def test_JsonModel_custom_cache(self):
        # Adding an item to the cache in the initialize method results in it
        # being in the cache.
        class ProductModelTestView(BaseProductModelTestView):
            def initialize(self):
                request = get_current_browser_request()
                target_info = {}
                target_info['title'] = "The Title"
                cache = IJSONRequestCache(request).objects
                cache['target_info'] = target_info
        canonical.launchpad.webapp.tests.ProductModelTestView = \
            ProductModelTestView
        self.configZCML()
        browser = self.getUserBrowser(self.url)
        cache = loads(browser.contents)
        self.assertThat(cache, KeysEqual('context', 'target_info'))

    def test_JsonModel_custom_cache_wrong_method(self):
        # Adding an item to the cache in some other method is not recognized,
        # even if it called as part of normal rendering.
        class ProductModelTestView(BaseProductModelTestView):
            def initialize(self):
                request = get_current_browser_request()
                target_info = {}
                target_info['title'] = "The Title"
                cache = IJSONRequestCache(request).objects
                cache['target_info'] = target_info

            def render(self):
                request = get_current_browser_request()
                other_info = {}
                other_info['spaz'] = "Stuff"
                IJSONRequestCache(request).objects['other_info'] = other_info

        canonical.launchpad.webapp.tests.ProductModelTestView = \
            ProductModelTestView
        self.configZCML()
        browser = self.getUserBrowser(self.url)
        cache = loads(browser.contents)
        self.assertThat(cache, KeysEqual('context', 'target_info'))
