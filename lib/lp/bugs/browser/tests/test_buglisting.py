# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    find_tags_by_class,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestBugTaskSearchListingPage(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def _makeDistributionSourcePackage(self):
        distro = self.factory.makeDistribution('test-distro')
        return self.factory.makeDistributionSourcePackage('test-dsp', distro)

    def test_distributionsourcepackage_unknown_bugtracker_message(self):
        # A DistributionSourcePackage whose Distro does not use
        # Launchpad for bug tracking should explain that.
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
        # A DistributionSourcePackage whose Distro does not use
        # Launchpad for bug tracking should not show the "Report a bug"
        # button.
        dsp = self._makeDistributionSourcePackage()
        url = canonical_url(dsp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None, find_tag_by_id(browser.contents, 'involvement'),
                      "Involvement portlet with Report-a-bug button should "
                      "not be shown")

    def test_distributionsourcepackage_unknown_bugtracker_no_filters(self):
        # A DistributionSourcePackage whose Distro does not use
        # Launchpad for bug tracking should not show links to "New
        # bugs", "Open bugs", etc.
        dsp = self._makeDistributionSourcePackage()
        url = canonical_url(dsp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None,
                      find_tag_by_id(browser.contents, 'portlet-bugfilters'),
                      "portlet-bugfilters should not be shown.")

    def test_distributionsourcepackage_unknown_bugtracker_no_tags(self):
        # A DistributionSourcePackage whose Distro does not use
        # Launchpad for bug tracking should not show links to search by
        # bug tags.
        dsp = self._makeDistributionSourcePackage()
        url = canonical_url(dsp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None, find_tag_by_id(browser.contents, 'portlet-tags'),
                      "portlet-tags should not be shown.")

    def _makeSourcePackage(self):
        distro = self.factory.makeDistribution('test-distro')
        series = self.factory.makeDistroRelease(
            distribution=distro, name='test-series')
        return self.factory.makeSourcePackage('test-sp', distro.currentseries)

    def test_sourcepackage_unknown_bugtracker_message(self):
        # A SourcePackage whose Distro does not use
        # Launchpad for bug tracking should explain that.
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
        # A SourcePackage whose Distro does not use Launchpad for bug
        # tracking should not show the "Report a bug" button.
        sp = self._makeSourcePackage()
        url = canonical_url(sp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None, find_tag_by_id(browser.contents, 'involvement'),
                      "Involvement portlet with Report-a-bug button should "
                      "not be shown")

    def test_sourcepackage_unknown_bugtracker_no_filters(self):
        # A SourcePackage whose Distro does not use Launchpad for bug
        # tracking should not show links to "New bugs", "Open bugs",
        # etc.
        sp = self._makeSourcePackage()
        url = canonical_url(sp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None,
                      find_tag_by_id(browser.contents, 'portlet-bugfilters'),
                      "portlet-bugfilters should not be shown.")

    def test_sourcepackage_unknown_bugtracker_no_tags(self):
        # A SourcePackage whose Distro does not use Launchpad for bug
        # tracking should not show links to search by bug tags.
        sp = self._makeSourcePackage()
        url = canonical_url(sp, rootsite='bugs')
        browser = self.getUserBrowser(url)
        self.assertIs(None,
                      find_tag_by_id(browser.contents, 'portlet-tags'),
                      "portlet-tags should not be shown.")


class TestBugTaskSearchListingView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_external_bugtracker_is_none(self):
        bug_target = self.factory.makeProduct()
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(None, view.external_bugtracker)

    def test_external_bugtracker(self):
        bug_target = self.factory.makeProduct()
        with person_logged_in(bug_target.owner):
            bug_target.bugtracker = self.factory.makeBugTracker()
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(bug_target.bugtracker, view.external_bugtracker)
