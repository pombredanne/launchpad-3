# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the TALES formatters."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp import canonical_url
from lp.testing import TestCaseWithFactory
from lp.app.browser.tales import PillarFormatterAPI


class TestPillarFormatterAPI(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    FORMATTER_CSS_CLASS = u'sprite product'

    def setUp(self):
        super(TestPillarFormatterAPI, self).setUp()
        self.product = self.factory.makeProduct()
        self.formatter = PillarFormatterAPI(self.product)
        self.product_url = canonical_url(self.product, 
            path_only_if_possible=True)

    def test_link(self):
        link = self.formatter.link(None)
        template = u'<a href="%(url)s" class="%(css_class)s">%(summary)s</a>'
        mapping = {
            'url': self.product_url,
            'summary': self.product.displayname,
            'css_class': self.FORMATTER_CSS_CLASS,
        }
        self.assertEquals(link, template % mapping)
        
    def test_link_with_displayname(self):
        link = self.formatter.link_with_displayname(None)
        template = (
            u'<a href="%(url)s" class="%(css_class)s">%(summary)s</a>'
            u'&nbsp;(<a href="%(url)s">%(name)s</a>)'
            )
        mapping = {
            'url': self.product_url,
            'summary': self.product.displayname,
            'name': self.product.name,
            'css_class': self.FORMATTER_CSS_CLASS,
        }
        self.assertEquals(link, template % mapping)
