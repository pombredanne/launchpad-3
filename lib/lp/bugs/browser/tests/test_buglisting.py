# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    find_tags_by_class,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import BrowserTestCase


class TestBugTaskSearchListingView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def _makeDistributionSourcePackage(self):
        distro = self.factory.makeDistribution('test-distro')
        return self.factory.makeDistributionSourcePackage('test-dsp', distro)

    def test_distributionsourcepackage_unknown_bugtracker_message(self):
        dsp = self._makeDistributionSourcePackage()
        url = canonical_url(dsp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        top_portlet = find_tags_by_class(
            browser.contents, 'top-portlet')
        self.assertTrue(len(top_portlet) > 0,
                        "Tag with class=top-portlet not found")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            test-dsp in test-distro does not use Launchpad for bug tracking.
            Getting started with bug tracking in Launchpad.""",
            extract_text(top_portlet[0]))

    def test_distributionsourcepackage_unknown_bugtracker_no_button(self):
        dsp = self._makeDistributionSourcePackage()
        url = canonical_url(dsp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None, find_tag_by_id(browser.contents, 'involvement'),
                      "Involvement portlet with Report-a-bug button should "
                      "not be shown")

    def _makeSourcePackage(self):
        distro = self.factory.makeDistribution('test-distro')
        series = self.factory.makeDistroRelease(
            distribution=distro, name='test-series')
        return self.factory.makeSourcePackage('test-sp', distro.currentseries)

    def test_sourcepackage_unknown_bugtracker_message(self):
        sp = self._makeSourcePackage()
        url = canonical_url(sp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        top_portlet = find_tags_by_class(
            browser.contents, 'top-portlet')
        self.assertTrue(len(top_portlet) > 0,
                        "Tag with class=top-portlet not found")
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            test-sp in Test-distro Test-series does not
            use Launchpad for bug tracking.
            Getting started with bug tracking in Launchpad.""",
            extract_text(top_portlet[0]))

    def test_sourcepackage_unknown_bugtracker_no_button(self):
        sp = self._makeSourcePackage()
        url = canonical_url(sp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None, find_tag_by_id(browser.contents, 'involvement'),
                      "Involvement portlet with Report-a-bug button should "
                      "not be shown")
