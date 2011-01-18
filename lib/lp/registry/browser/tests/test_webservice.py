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


class TestPersonRenderer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_person_renderer(self):
        # A person renderer will result in the same text as a TALES
        # PersonFormatter.
        eric = self.factory.makePerson(name='eric')
        # We need something that has an IPersonChoice, a project will do.
        product = self.factory.makeProduct(owner=eric)
        field = IProduct['owner']
        request = get_current_web_service_request()
        renderer = getMultiAdapter(
            (product, field, request), IFieldHTMLRenderer)
        # The person renderer gives the same result as the TALES formatter.
        self.assertEqual('%s' % format_link(eric), renderer(None))
