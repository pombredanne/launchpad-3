# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the TALES formatters."""

__metaclass__ = type

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.tales import PillarFormatterAPI
from lp.testing import TestCaseWithFactory


class TestPillarFormatterAPI(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    FORMATTER_CSS_CLASS = u'sprite product'

    def setUp(self):
        super(TestPillarFormatterAPI, self).setUp()
        self.product = self.factory.makeProduct()
        self.formatter = PillarFormatterAPI(self.product)
        self.product_url = canonical_url(
            self.product, path_only_if_possible=True)

    def test_link(self):
        # Calling PillarFormatterAPI.link() will return a link to the
        # current context, formatted to include a custom icon if the
        # context has one, and to display the context summary.
        link = self.formatter.link(None)
        template = u'<a href="%(url)s" class="%(css_class)s">%(summary)s</a>'
        mapping = {
            'url': self.product_url,
            'summary': self.product.displayname,
            'css_class': self.FORMATTER_CSS_CLASS,
            }
        self.assertEquals(link, template % mapping)

    def test_link_with_displayname(self):
        # Calling PillarFormatterAPI.link_with_displayname() will return
        # a link to the current context, formatted to include a custom icon
        # if the context has one, and to display a descriptive summary
        # (displayname and name of the context).
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
