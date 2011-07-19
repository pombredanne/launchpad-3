# Copyright 2011 Canonical Ltd.  All rights reserved.

"""Tests for the user requested oops using ++oops++ traversal."""

__metaclass__ = type


from lazr.restful.utils import get_current_browser_request
from zope.location.interfaces import LocationError

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.app.browser.launchpadform import LaunchpadFormView
from canonical.launchpad.webapp.namespace import JsonModelNamespaceView
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    logout,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view

class FakeView:
    """A view object that just has a fake context and request."""

    def __init__(self):
        self.context = object()
        self.request = object()


class TestJsonModelNamespace(TestCaseWithFactory):

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
        request = get_current_browser_request
        context = object()
        view = FakeView()
        namespace = JsonModelNamespaceView(context, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)

    def test_JsonModelNamespace_traverse_LPView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request
        context = object()
        view = LaunchpadView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)

    def test_JsonModelNamespace_traverse_LPFormView(self):
        # Test traversal for JSON model namespace,
        # ++model++ for a non-LaunchpadView context.
        request = get_current_browser_request
        context = object()
        view = LaunchpadFormView(context, request)
        namespace = JsonModelNamespaceView(view, request)
        result = namespace.traverse(view, None)
        self.assertEqual(result, namespace)


from zope.configuration import xmlconfig
from zope.interface import (
    Attribute,
    implements,
    Interface,
    )
from zope.component import provideAdapter
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
import canonical.launchpad.webapp.tests


class ISchnizzle(Interface):
    name = Attribute("name")
    person = Attribute("person")

class Schnizzle:
    implements(ISchnizzle)
    def __init__(self, name, person):
        self.name = name
        self.person = person

class SchnizzleView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
    def initialize(self):
        pass

class TestJsonModelView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ANONYMOUS)

    def tearDown(self):
        logout()
        TestCaseWithFactory.tearDown(self)

    def test_JsonModel_view_cache(self):
        # Register the ZCML for our test view.
        for interface in [ISchnizzle]:
            name = interface.getName()
            setattr(canonical.launchpad.webapp.tests, name, interface)
            interface.__module__ = 'canonical.launchpad.webapp.tests'
        canonical.launchpad.webapp.tests.SchnizzleView = SchnizzleView
        xmlconfig.string("""
          <configure
              xmlns:browser="http://namespaces.zope.org/browser">
              <include package="canonical.launchpad.webapp"
                  file="meta.zcml" />
              <include package="zope.app.zcmlfiles" file="meta.zcml" />
              <browser:url
                for="canonical.launchpad.webapp.tests.ISchnizzle"
                path_expression="string:${name}"
                attribute_to_parent = "person" />
              <browser:defaultView
                for="canonical.launchpad.webapp.tests.ISchnizzle"
                name="+index"/>
              <browser:page
                name="+index"
                for="canonical.launchpad.webapp.tests.ISchnizzle"
                class="canonical.launchpad.webapp.tests.SchnizzleView"
                permission="zope.Public"
                />
          </configure>""")

        ## provideAdapter(SchnizzleView, (ISchnizzle, IDefaultBrowserLayer),
        ##     name="+schniz", provides=Interface)
        import pdb; pdb.set_trace(); # DO NOT COMMIT
        schniz = Schnizzle("sammy", self.factory.makePerson(name="schnoz"))
        view = create_initialized_view(schniz, name="+index")
        #view.render()
        url = canonical_url(schniz) + '/++model++'
        browser = self.getUserBrowser(url)
        print browser


class TestJsonModelBrowser(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_JsonModelNamespace_named_view(self):
        # Test the output of a named view.
        person = self.factory.makePerson(name="joe")
        url = canonical_url(person) + '/++model++'
        browser = self.getUserBrowser(url)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            {"context": {.*}}""", browser.contents)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            .*"self_link": "http://launchpad.dev/api/.*/~joe".*""",
            browser.contents)
