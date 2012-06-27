# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.browser.widgets.bug import BugTagsWidget
from lp.bugs.interfaces.bugtarget import IHasOfficialBugTags
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class BugTargetTagsMixinTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def get_widget(self, bug_target):
        field = IHasOfficialBugTags['official_bug_tags']
        bound_field = field.bind(bug_target)
        request = LaunchpadTestRequest()
        return BugTagsWidget(bound_field, None, request)

    def test_official_tags_js_not_adaptable_to_product_or_distro(self):
        # project groups are not full bug targets so they have no tags.
        project_group = self.factory.makeProject()
        view = self.get_widget(project_group)
        js = view.official_tags_js
        self.assertEqual('var official_tags = [];', js)

    def test_official_tags_js_product_without_tags(self):
        # Products without tags have an empty list.
        product = self.factory.makeProduct()
        view = self.get_widget(product)
        js = view.official_tags_js
        self.assertEqual('var official_tags = [];', js)

    def test_official_tags_js_product_with_tags(self):
        # Products with tags have a list of tags.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            product.official_bug_tags = [u'cows', u'pigs', u'sheep']
        view = self.get_widget(product)
        js = view.official_tags_js
        self.assertEqual('var official_tags = ["cows", "pigs", "sheep"];', js)

    def test_official_tags_js_distribution_without_tags(self):
        # Distributions without tags have an empty list.
        distribution = self.factory.makeDistribution()
        view = self.get_widget(distribution)
        js = view.official_tags_js
        self.assertEqual('var official_tags = [];', js)

    def test_official_tags_js_distribution_with_tags(self):
        # Distributions with tags have a list of tags.
        distribution = self.factory.makeDistribution()
        with person_logged_in(distribution.owner):
            distribution.official_bug_tags = [u'cows', u'pigs', u'sheep']
        view = self.get_widget(distribution)
        js = view.official_tags_js
        self.assertEqual('var official_tags = ["cows", "pigs", "sheep"];', js)
