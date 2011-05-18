# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductSeries pages."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    TestCaseWithFactory,
    person_logged_in
    )
from lp.testing.views import create_initialized_view
from lp.testing.matchers import Contains


class TestProductSeriesHelp(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer
    
    def test_new_series_help(self):
        # The LP branch URL displayed to the user on the +code-summary page for
        # a product series will relate to that series instead of to the default
        # series for the Product.
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        person = product.owner
        ssh_key = self.factory.makeSSHKey(person=person)
        branch_url = "lp:~%s/%s/%s" % (person.name, product.name, series.name)
        with person_logged_in(person):
            view = create_initialized_view(series, '+code-summary')
            self.assertThat(view(), Contains(branch_url))
