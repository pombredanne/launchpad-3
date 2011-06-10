# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the lp.app.browser.launchpadform module."""

__metaclass__ = type

from lxml import html
from z3c.ptcompat import ViewPageTemplateFile
from zope.interface import Interface
from zope.schema import Text

from canonical.config import config
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.launchpadform import (
    has_structured_doc,
    LaunchpadFormView,
    )
from lp.testing import (
    test_tales,
    TestCase,
    TestCaseWithFactory,
    )


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
        normal_widget, structured_widget = view.widgets
        self.assertIs(None, self._widget_annotation(normal_widget))
        self.assertTrue(self._widget_annotation(structured_widget))


class TestQueryTalesForHasStructuredDoc(TestCase):

    layer = DatabaseFunctionalLayer

    def test_query_tales(self):
        # Test that query:has-structured-doc gets sets the field annotation.
        request = LaunchpadTestRequest()
        view = TestView(None, request)
        view.initialize()
        normal_widget, structured_widget = view.widgets
        self.assertIs(None, test_tales(
                'widget/query:has-structured-doc', widget=normal_widget))
        self.assertTrue(test_tales(
                'widget/query:has-structured-doc', widget=structured_widget))


class TestHelpLinksInterface(Interface):
    """Test interface for the view below."""

    nickname = Text(title=u'nickname')

    displayname = Text(title=u'displayname')


class TestHelpLinksView(LaunchpadFormView):
    """A trivial view that contains help links."""

    schema = TestHelpLinksInterface

    page_title = u"TestHelpLinksView"
    template = ViewPageTemplateFile(
        config.root + '/lib/lp/app/templates/generic-edit.pt')

    help_links = {
        "nickname": u"http://widget.example.com/name",
        "displayname": u"http://widget.example.com/displayname",
        }


class TestHelpLinks(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_help_links_on_widget(self):
        # The values in a view's help_links dictionary gets copied into the
        # corresponding widgets' help_link attributes.
        request = LaunchpadTestRequest()
        view = TestHelpLinksView(None, request)
        view.initialize()
        nickname_widget, displayname_widget = view.widgets
        self.assertEqual(
            u"http://widget.example.com/name",
            nickname_widget.help_link)
        self.assertEqual(
            u"http://widget.example.com/displayname",
            displayname_widget.help_link)

    def test_help_links_render(self):
        # The values in a view's help_links dictionary are rendered in the
        # default generic-edit template.
        user = self.factory.makePerson()
        request = LaunchpadTestRequest(PATH_INFO="/")
        request.setPrincipal(user)
        view = TestHelpLinksView(user, request)
        view.initialize()
        root = html.fromstring(view.render())
        [nickname_help_link] = root.cssselect(
            "label[for$=nickname] ~ a[target=help]")
        self.assertEqual(
            u"http://widget.example.com/name",
            nickname_help_link.get("href"))
        [displayname_help_link] = root.cssselect(
            "label[for$=displayname] ~ a[target=help]")
        self.assertEqual(
            u"http://widget.example.com/displayname",
            displayname_help_link.get("href"))
