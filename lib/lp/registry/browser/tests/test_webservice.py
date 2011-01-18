# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.registry.browser.webservice."""

__metaclass__ = type


from lazr.restful.interfaces import IFieldHTMLRenderer
from lazr.restful.utils import get_current_web_service_request
from zope.component import getMultiAdapter

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.tales import format_link
from lp.registry.interfaces.product import IProduct
from lp.testing import TestCaseWithFactory


class TestXHTMLRepresentations(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_person(self):
        # Test the XHTML representation of a person.
        eric = self.factory.makePerson()
        # The representation of a person is the same as a tales PersonFormatter.
        self.assertEqual(
            '<span>%s</span>' % format_link(eric), renderer(eric))

    def test_text(self):
        # Test the XHTML representation of a text field.
        text = u'\N{SNOWMAN} snowman@example.com'
        # We need something that has an IPersonChoice, a project will do.
        product = self.factory.makeProduct()
        field = IProduct['description']
        request = get_current_web_service_request()
        renderer = getMultiAdapter(
            (product, field, request), IFieldHTMLRenderer)
        # The representation is UTF-8 encoded with hidden email.
        self.assertEqual(
            '<p>\xe2\x98\x83 &lt;email address hidden&gt;</p>',
            renderer(text))

