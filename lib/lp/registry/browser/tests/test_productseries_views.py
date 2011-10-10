# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductSeries pages."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import BugTaskStatus
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


class TestProductSeriesStats(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_bugtask_status_counts(self):
        """Test that `bugtask_status_counts` is sane."""
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        for status in BugTaskStatus.items:
            self.factory.makeBug(
                series=series, status=status, owner=product.owner)
        with person_logged_in(product.owner):
            view = create_initialized_view(series, '+status')
            self.assertEqual([], view.bugtask_status_counts)  # TODO
