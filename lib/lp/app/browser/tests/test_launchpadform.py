# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the lp.app.browser.launchpadform module."""

__metaclass__ = type

from zope.interface import Interface
from zope.schema import Text

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.launchpadform import (
    has_structured_doc,
    LaunchpadFormView,
    )
from lp.testing import TestCase, test_tales


class TestInterface(Interface):
    """Test interface for the view below."""

    normal = Text(title=u'normal', description=u'plain text')

    structured = has_structured_doc(
        Text(title=u'structured',
             description=u'<strong>structured text</strong'))


class TestView(LaunchpadFormView):
    """A trivial view using the TestInterface."""

    schema = TestInterface


class TestHasStructuredDoc(TestCase):

    layer = DatabaseFunctionalLayer

    def _widget_annotation(self, widget):
        return widget.context.queryTaggedValue('has_structured_doc')

    def test_has_structured_doc_sets_attribute(self):
        # Test that has_structured_doc sets the field annotation.
        request = LaunchpadTestRequest()
        view = TestView(None, request)
        view.initialize()
        normal_widget, structured_widget = list(view.widgets)
        self.assertIs(None, self._widget_annotation(normal_widget))
        self.assertTrue(self._widget_annotation(structured_widget))


class TestQueryTalesForHasStructuredDoc(TestCase):

    layer = DatabaseFunctionalLayer

    def test_query_tales(self):
        # Test that query:has-structured-doc gets sets the field annotation.
        request = LaunchpadTestRequest()
        view = TestView(None, request)
        view.initialize()
        normal_widget, structured_widget = list(view.widgets)
        self.assertIs(None, test_tales(
                'widget/query:has-structured-doc', widget=normal_widget))
        self.assertTrue(test_tales(
                'widget/query:has-structured-doc', widget=structured_widget))
