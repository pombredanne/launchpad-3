# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for DistributionUpstreamReport."""

__metaclass__ = type


from soupmatchers import (
    HTMLContains,
    Tag,
    )
from testtools.matchers import Not
from zope.component import getUtility

from lp.app.enums import ServiceUsage
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.browser.distribution_upstream_report import (
    BugReportData,
    DistributionUpstreamReport,
    )
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.views import (
    create_view,
    create_initialized_view,
    )


class BugReportDataTestCase(TestCase):

    def make_bug_report_data(self):
        return BugReportData(
            open_bugs=90, triaged_bugs=50, upstream_bugs=70, watched_bugs=60)

    def test_init(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual(90, bug_data.open_bugs)
        self.assertEqual(50, bug_data.triaged_bugs)
        self.assertEqual(70, bug_data.upstream_bugs)
        self.assertEqual(60, bug_data.watched_bugs)

    def test_percentage_properties(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual(55.56, bug_data.triaged_bugs_percentage)
        self.assertEqual(77.78, bug_data.upstream_bugs_percentage)
        self.assertEqual(85.71, bug_data.watched_bugs_percentage)

    def test_as_percentage(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual(55.56, bug_data._as_percentage(50, 90))
        self.assertEqual(0.0, bug_data._as_percentage(50, 0))

    def test_delta_properties(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual(40, bug_data.triaged_bugs_delta)
        self.assertEqual(20, bug_data.upstream_bugs_delta)
        self.assertEqual(10, bug_data.watched_bugs_delta)

    def test_as_value_class(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual('good', bug_data._as_value_class(60, 50))
        self.assertEqual('', bug_data._as_value_class(50, 50))
        self.assertEqual('', bug_data._as_value_class(40, 50))

    def test_value_class(self):
        bug_data = self.make_bug_report_data()
        bug_data.watched_bugs = 80
        self.assertEqual('', bug_data.triaged_bugs_class)
        self.assertEqual('', bug_data.upstream_bugs_class)
        self.assertEqual('good', bug_data.watched_bugs_class)

    def test_row_class(self):
        bug_data = self.make_bug_report_data()
        self.assertEqual('', bug_data.row_class)
        bug_data.watched_bugs = 80
        self.assertEqual('good', bug_data.row_class)
        bug_data.watched_bugs = 11
        self.assertEqual('bad', bug_data.row_class)


class TestDistributionUpstreamReport(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_valid_sort_keys_are_valid(self):
        # The valid_sort_keys property of the
        # DistributionUpstreamReport view contains a list of the sort
        # keys that the view considers valid. Using any one of these
        # keys, including when prepended with a '-', will lead to it
        # being set as the view's sort_order key.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        for sort_key in DistributionUpstreamReport.valid_sort_keys:
            form = {'sort_by': sort_key}
            view = create_view(ubuntu, '+upstreamreport', form)

            # The sort_order property of DistributionUpstreamReport is
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
        # The property DistributionUpstreamReport.has_upstream_report
        # is False if a distribution does not use Launchpad for bug
        # tracking and if no current distroseries exists.
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+upstreamreport')
        self.assertNotEqual(
            ServiceUsage.LAUNCHPAD, distribution.bug_tracking_usage)
        self.assertIs(None, distribution.currentseries)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__no_distroseries_with_bug_tracking(self):
        # The property DistributionUpstreamReport.has_upstream_report
        # is False if a distribution does not have a current
        # distroseries, even if Luanchpad is used for bug tracking.
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+upstreamreport')
        with person_logged_in(distribution.owner):
            distribution.official_malone = True
        self.assertIs(None, distribution.currentseries)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__with_distroseries_no_bug_tracking(self):
        # The property DistributionUpstreamReport.has_upstream_report
        # is False if a distribution has a current distroseries, but
        # if Launchpad is not used for bug tracking.
        distribution = self.factory.makeDistroSeries().distribution
        view = create_initialized_view(distribution, '+upstreamreport')
        self.assertIsNot(None, distribution.currentseries)
        self.assertNotEqual(
            ServiceUsage.LAUNCHPAD, distribution.bug_tracking_usage)
        self.assertFalse(view.has_upstream_report)

    def test_has_upstream_report__with_distroseries_and_bug_tracking(self):
        # The property DistributionUpstreamReport.has_upstream_report
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


class TestDistributionUpstreamReportPage(BrowserTestCase):
    """Tests for the +upstream report page."""

    layer = LaunchpadFunctionalLayer

    def getTagMatchers(self):
        """Return matchers for the tag saying "launchpad is not used
        for development" and the tag containing the upstream report."""
        no_lp_usage = Tag(
            'no-lp-usage', 'div', attrs={'id': 'no-lp-usage'})
        no_bugs_filed = Tag('lp-used', 'div', attrs={'id': 'lp-used'})
        return no_lp_usage, no_bugs_filed

    def test_no_upstream_report_for_unconfigured_distros(self):
        # If DistributionUpstreamReport.has_upstream_report is False,
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
        # If DistributionUpstreamReport.has_upstream_report is True,
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
