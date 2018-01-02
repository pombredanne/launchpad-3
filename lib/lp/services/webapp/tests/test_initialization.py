# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests post-zcml application initialization.

As found in lp.services.webapp.initialization.py."""

from zope.component import getSiteManager
from zope.interface import Interface
from zope.publisher import browser
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.interfaces import ITraversable

from lp.services.webapp.errorlog import OopsNamespace
from lp.services.webapp.interfaces import IUnloggedException
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCase
from lp.testing.layers import FunctionalLayer


class AnyObject:
    pass


class TestURLNamespace(TestCase):

    layer = FunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        self.sm = getSiteManager()
        self.context = AnyObject()
        self.request = LaunchpadTestRequest()

    def test_oops_namespace_not_view(self):
        # The ++oops++ namespace should not be available as a "oops" view.
        # First, we will verify that it is available as a namespace.
        namespace = self.sm.getMultiAdapter(
            (self.context, self.request), ITraversable, 'oops')
        self.assertTrue(isinstance(namespace, OopsNamespace))
        # However, it is not available as a view.
        not_a_namespace = self.sm.queryMultiAdapter(
            (self.context, self.request), Interface, 'oops')
        self.assertFalse(isinstance(not_a_namespace, OopsNamespace))

    def test_no_namespaces_are_views(self):
        # This tests an abstract superset of test_oops_namespace_not_view.
        # At the time of writing, namespaces were 'resource', 'oops', 'form',
        # and 'view'.
        namespace_info = self.sm.adapters.lookupAll(
            (Interface, IBrowserRequest), ITraversable)
        for name, factory in namespace_info:
            try:
                not_the_namespace_factory = self.sm.adapters.lookup(
                    (Interface, IBrowserRequest), Interface, name)
            except LookupError:
                pass
            else:
                self.assertNotEqual(factory, not_the_namespace_factory)


class TestWrappedParameterConverter(TestCase):
    """Make sure URL parameter type conversions don't generate OOPS reports"""

    layer = FunctionalLayer

    def test_return_value_untouched(self):
        # When a converter succeeds, its return value is passed through the
        # wrapper untouched.
        converter = browser.get_converter('int')
        self.assertEqual(42, converter('42'))

    def test_value_errors_marked(self):
        # When a ValueError is raised by the wrapped converter, the exception
        # is marked with IUnloggedException so the OOPS machinery knows that a
        # report should not be logged.
        converter = browser.get_converter('int')
        try:
            converter('not an int')
        except ValueError as e:
            self.assertTrue(IUnloggedException.providedBy(e))

    def test_other_errors_not_marked(self):
        # When an exception other than ValueError is raised by the wrapped
        # converter, the exception is not marked with IUnloggedException an
        # OOPS report will be created.
        class BadString:
            def __str__(self):
                raise RuntimeError

        converter = browser.get_converter('string')
        try:
            converter(BadString())
        except RuntimeError as e:
            self.assertFalse(IUnloggedException.providedBy(e))

    def test_none_is_not_wrapped(self):
        # The get_converter function that we're wrapping can return None, in
        # that case there's no function for us to wrap and we just return None
        # as well.
        converter = browser.get_converter('unregistered')
        self.assertIsNone(converter)
