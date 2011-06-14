# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for DistributionUpstreamBugReport."""

__metaclass__ = type


from soupmatchers import (
    HTMLContains,
    Tag,
    )
from testtools.matchers import Not
from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    logout,
    )
from canonical.launchpad.testing.systemdocs import create_view
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.enums import ServiceUsage
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.browser.distribution_upstream_bug_report import (
    DistributionUpstreamBugReport,
    )
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestDistributionUpstreamBugReport(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestDistributionUpstreamBugReport, self).setUp()
        login(ANONYMOUS)

    def tearDown(self):
        logout()
        super(TestDistributionUpstreamBugReport, self).tearDown()

    def test_valid_sort_keys_are_valid(self):
        # The valid_sort_keys property of the
        # DistributionUpstreamBugReport view contains a list of the sort
        # keys that the view considers valid. Using any one of these
        # keys, including when prepended with a '-', will lead to it
        # being set as the view's sort_order key.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        for sort_key in DistributionUpstreamBugReport.valid_sort_keys:
            form = {'sort_by': sort_key}
            view = create_view(ubuntu, '+upstreamreport', form)

            # The sort_order property of DistributionUpstreamBugReport is
            # a tuple in the form (sort_key, reversed).
            view_sort_key, view_sort_reversed = view.sort_order
            self.assertEqual(view_sort_key, sort_key,
                "Expected a sort_key of '%s', got '%s'" %
                (sort_key, view_sort_key))

            # By default, reversed is False.
            self.assertFalse(view_sort_reversed,
                "Sort order should not be reversed for a sort_by value of "
                "%s" % sort_key)

            # Prepending a '-' to sort_by will reverse the sort.
            reversed_key = '-%s' % sort_key
            form = {'sort_by': reversed_key}
            view = create_view(ubuntu, '+upstreamreport', form)

            # The sort_key part of view.sort_order will be the same as
            # for a normal sort.
            view_sort_key, view_sort_reversed = view.sort_order
            self.assertEqual(view_sort_key, sort_key,
                "Expected a sort_key of '%s', got '%s'" %
                (sort_key, view_sort_key))

            # But reversed is now True.
            self.assertTrue(view_sort_reversed,
                "Sort order should be reversed for a sort_by value of "
                "%s" % reversed_key)

    def test_has_upstream_report__no_series_no_bug_tracking(self):
        # The property DistributionUpstreamBugReport.has_upstream_report
        # is False if a distribution does not use Launchpad for bug
        # tracking and if no current distroseries exists.
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+upstreamreport')
        self.assertNotEqual(
            ServiceUsage.LAUNCHPAD, distribution.bug_tracking_usage)
        self.assertIs(None, distribution.currentseries)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__no_distroseries_with_bug_tracking(self):
        # The property DistributionUpstreamBugReport.has_upstream_report
        # is False if a distribution does not have a current
        # distroseries, even if Luanchpad is used for bug tracking.
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+upstreamreport')
        with person_logged_in(distribution.owner):
            distribution.official_malone = True
        self.assertIs(None, distribution.currentseries)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__with_distroseries_no_bug_tracking(self):
        # The property DistributionUpstreamBugReport.has_upstream_report
        # is False if a distribution has a current distroseries, but
        # if Launchpad is not used for bug tracking.
        distribution = self.factory.makeDistroSeries().distribution
        view = create_initialized_view(distribution, '+upstreamreport')
        self.assertIsNot(None, distribution.currentseries)
        self.assertNotEqual(
            ServiceUsage.LAUNCHPAD, distribution.bug_tracking_usage)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__with_distroseries_and_bug_tracking(self):
        # The property DistributionUpstreamBugReport.has_upstream_report
        # is True if a distribution has a current distroseries and if it
        # uses Launchpad for bug tracking.
        distribution = self.factory.makeDistroSeries().distribution
        with person_logged_in(distribution.owner):
            distribution.official_malone = True
        view = create_initialized_view(distribution, '+upstreamreport')
        self.assertIsNot(None, distribution.currentseries)
        self.assertEqual(
            ServiceUsage.LAUNCHPAD, distribution.bug_tracking_usage)
        self.assertTrue(view.has_upstream_report)


class TestDistributionUpstreamBugReportPage(BrowserTestCase):

    """Tests for the +upstream bug report page."""

    layer = LaunchpadFunctionalLayer

    def getTagMatchers(self):
        """Return matchers for the tag saying "launchpad is not used
        for development" and the tag containing the upstream report."""
        no_lp_usage = Tag(
            'no-lp-usage', 'div', attrs={'id': 'no-lp-usage'})
        no_bugs_filed = Tag('lp-used', 'div', attrs={'id': 'lp-used'})
        return no_lp_usage, no_bugs_filed

    def test_no_upstream_report_for_unconfigured_distros(self):
        # If DistributionUpstreamBugReport.has_upstream_report is False,
        # the +upstream-report page does not show the report.
        distribution = self.factory.makeDistribution()
        browser = self.getViewBrowser(
            distribution, '+upstreamreport', no_login=True)
        no_lp_usage, no_bugs_filed = self.getTagMatchers()
        self.assertThat(browser.contents, Not(HTMLContains(no_bugs_filed)))
        # Instead, a message tells the user that no report is
        # available.
        self.assertThat(browser.contents, HTMLContains(no_lp_usage))

    def test_upstream_report_for_configured_distros(self):
        # If DistributionUpstreamBugReport.has_upstream_report is True,
        # the +upstream-report page does shows the report.
        distribution = self.factory.makeDistroSeries().distribution
        with person_logged_in(distribution.owner):
            distribution.official_malone = True
        browser = self.getViewBrowser(
            distribution, '+upstreamreport', no_login=True)
        no_lp_usage, no_bugs_filed = self.getTagMatchers()
        self.assertThat(browser.contents, HTMLContains(no_bugs_filed))
        # A message telling the user that no report is available
        # is not shown.
        self.assertThat(browser.contents, Not(HTMLContains(no_lp_usage)))
