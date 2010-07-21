# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for base-layout.pt and its macros.

The base-layout master template defines macros that control the layout
of the page. Any page can use these layout options by including

    metal:use-macro='view/macro:page/<layout>"

in the root element. The template provides common layout to Launchpad.
"""

__metaclass__ = type

import unittest

from BeautifulSoup import BeautifulSoup

from z3c.ptcompat import ViewPageTemplateFile

from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import find_tag_by_id

from lp.testing import TestCaseWithFactory


class TestBaseLayout(TestCaseWithFactory):
    """Test for the ILaunchpadRoot permission"""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBaseLayout, self).setUp()
        self.user = self.factory.makePerson(name='waffles')
        self.request = LaunchpadTestRequest(
            SERVER_URL='http://launchpad.dev',
            PATH_INFO='/~waffles/+layout')
        self.request.setPrincipal(self.user)

    def makeTemplateView(self, layout):
        """Return a view that uses the specified layout."""

        class TemplateView(LaunchpadView):
            """A simple view to test base-layout."""
            __launchpad_facetname__ = 'overview'
            template = ViewPageTemplateFile(
                'testfiles/%s.pt' % layout.replace('_', '-'))
            page_title = 'Test base-layout: %s' % layout

        return TemplateView(self.user, self.request)

    def test_base_layout_doctype(self):
        # Verify that the document is a html DOCTYPE.
        view = self.makeTemplateView('main_side')
        markup = view()
        self.assertTrue(markup.startswith('<!DOCTYPE html'))

    def verify_base_layout_common(self, view, content):
        # The html element states the namespace and language information.
        self.assertEqual(
            'http://www.w3.org/1999/xhtml', content.html['xmlns'])
        html_tag = content.html
        self.assertEqual('en', html_tag['xml:lang'])
        self.assertEqual('en', html_tag['lang'])
        self.assertEqual('ltr', html_tag['dir'])
        # The page's title starts with the view's page_title.
        self.assertTrue(content.title.string.startswith(view.page_title))
        # The shortcut icon for the browser chrome is provided.
        link_tag = content.link
        self.assertEqual('shortcut icon', link_tag['rel'])
        self.assertEqual('/@@/launchpad.png', link_tag['href'])
        # The template loads the common scripts.
        load_script = find_tag_by_id(content, 'base-layout-load-scripts').name
        self.assertEqual('script', load_script)

    def verify_main_content(self, document):
        self.assertEqual('body', document.name)
        yui_layout = document.find('div', 'yui-d0')
        self.assertTrue(yui_layout is not None)
        self.assertEqual(
            'login-logout', yui_layout.find(True, id='locationbar')['class'])
        self.assertEqual(
            'yui-main', yui_layout.find(True, id='maincontent')['class'])
        self.assertEqual(
            'invisible', document.find(True, id='help-pane')['class'])
        self.assertEqual(
            'footer', yui_layout.find(True, id='footer')['class'])

    def verify_watermark(self, document):
        yui_layout = document.find('div', 'yui-d0')
        watermark = yui_layout.find(True, id='watermark')
        self.assertEqual('watermark-apps-portlet', watermark['class'])
        self.assertEqual('/@@/person-logo', watermark.img['src'])
        self.assertEqual('Waffles', watermark.h2.string)
        self.assertEqual('facetmenu', watermark.ul['class'])
        self.assertEqual(
            'registering', watermark.find(True, id='registration')['class'])

    def test_main_side(self):
        view = self.makeTemplateView('main_side')
        content = BeautifulSoup(view())
        self.verify_base_layout_common(view, content)
        document = find_tag_by_id(content, 'document')
        self.verify_main_content(document)
        self.verify_watermark(document)
        classes = 'tab-overview main_side public yui-skin-sam'.split()
        self.assertEqual(classes, document['class'].split())
        self.assertEqual(
            'yui-b side', document.find(True, id='side-portlets')['class'])
        self.assertEqual('form', document.find(True, id='globalsearch').name)

    def test_main_only(self):
        view = self.makeTemplateView('main_only')
        content = BeautifulSoup(view())
        self.verify_base_layout_common(view, content)
        document = find_tag_by_id(content, 'document')
        self.verify_main_content(document)
        self.verify_watermark(document)
        classes = 'tab-overview main_only public yui-skin-sam'.split()
        self.assertEqual(classes, document['class'].split())
        self.assertEqual(None, document.find(True, id='side-portlets'))
        self.assertEqual('form', document.find(True, id='globalsearch').name)

    def test_searchless(self):
        view = self.makeTemplateView('searchless')
        content = BeautifulSoup(view())
        self.verify_base_layout_common(view, content)
        document = find_tag_by_id(content, 'document')
        self.verify_main_content(document)
        self.verify_watermark(document)
        classes = 'tab-overview searchless public yui-skin-sam'.split()
        self.assertEqual(classes, document['class'].split())
        self.assertEqual(None, document.find(True, id='side-portlets'))
        self.assertEqual(None, document.find(True, id='globalsearch'))

    def test_locationless(self):
        view = self.makeTemplateView('locationless')
        content = BeautifulSoup(view())
        self.verify_base_layout_common(view, content)
        document = find_tag_by_id(content, 'document')
        self.verify_main_content(document)
        classes = 'tab-overview locationless public yui-skin-sam'.split()
        self.assertEqual(classes, document['class'].split())
        self.assertEqual(None, document.find(True, id='watermark'))
        self.assertEqual(None, document.find(True, id='side-portlets'))
        self.assertEqual(None, document.find(True, id='globalsearch'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
