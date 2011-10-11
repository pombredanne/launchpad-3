# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductSeries pages."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    BugTaskStatusSearch,
    )
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.matchers import Contains
from lp.testing.views import create_initialized_view


class TestProductSeriesHelp(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_new_series_help(self):
        # The LP branch URL displayed to the user on the +code-summary page
        # for a product series will relate to that series instead of to the
        # default series for the Product.
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        person = product.owner
        self.factory.makeSSHKey(person=person)
        branch_url = "lp:~%s/%s/%s" % (person.name, product.name, series.name)
        with person_logged_in(person):
            view = create_initialized_view(series, '+code-summary')
            self.assertThat(view(), Contains(branch_url))


class TestWithBrowser(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_timeline_graph(self):
        """Test that rendering the graph does not raise an exception."""
        productseries = self.factory.makeProductSeries()
        self.getViewBrowser(productseries, view_name='+timeline-graph')


class TestProductSeriesStatus(TestCaseWithFactory):
    """Tests for ProductSeries:+status."""

    layer = DatabaseFunctionalLayer

    def test_bugtask_status_counts(self):
        """Test that `bugtask_status_counts` is sane."""
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        for status in BugTaskStatusSearch.items:
            self.factory.makeBug(
                series=series, status=status,
                owner=product.owner)
        self.factory.makeBug(
            series=series, status=BugTaskStatus.UNKNOWN,
            owner=product.owner)
        with person_logged_in(product.owner):
            view = create_initialized_view(series, '+status')
            self.assertEqual(
                [(BugTaskStatus.NEW, 1),
                 (BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE, 1),
                 # 2 because INCOMPLETE is stored as INCOMPLETE_WITH_RESPONSE
                 # or INCOMPLETE_WITHOUT_RESPONSE, and there was no response
                 # for the bug created as INCOMPLETE.
                 (BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE, 2),
                 (BugTaskStatus.OPINION, 1),
                 (BugTaskStatus.INVALID, 1),
                 (BugTaskStatus.WONTFIX, 1),
                 (BugTaskStatus.EXPIRED, 1),
                 (BugTaskStatus.CONFIRMED, 1),
                 (BugTaskStatus.TRIAGED, 1),
                 (BugTaskStatus.INPROGRESS, 1),
                 (BugTaskStatus.FIXCOMMITTED, 1),
                 (BugTaskStatus.FIXRELEASED, 1),
                 (BugTaskStatus.UNKNOWN, 1)],
                [(status_count.status, status_count.count)
                 for status_count in view.bugtask_status_counts],
                )
