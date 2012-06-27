# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.browser.bugtask import BugTargetTagsMixin
from lp.bugs.publisher import BugsLayer
from lp.services.webapp.publisher import LaunchpadView
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_view


class TestBugTargetTags(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTargetTags, self).setUp()
        self.project = self.factory.makeProject()
        self.target_product = self.factory.makeProduct(project=self.project)

    def test_no_tags(self):
        self.factory.makeBug(product=self.target_product)
        view = create_view(
            self.project,
            name="+bugtarget-portlet-tags-content",
            layer=BugsLayer)
        self.assertEqual([], [tag['tag'] for tag in view.tags_cloud_data])

    def test_tags(self):
        self.factory.makeBug(product=self.target_product, tags=['foo'])
        view = create_view(
            self.project,
            name="+bugtarget-portlet-tags-content",
            layer=BugsLayer)
        self.assertEqual(
            [u'foo'],
            [tag['tag'] for tag in view.tags_cloud_data])

    def test_tags_order(self):
        """Test that the tags are ordered by most used first"""
        self.factory.makeBug(product=self.target_product, tags=['tag-last'])
        for counter in range(0, 2):
            self.factory.makeBug(
                product=self.target_product, tags=['tag-middle'])
        for counter in range(0, 3):
            self.factory.makeBug(
                product=self.target_product, tags=['tag-first'])
        view = create_view(
            self.project,
            name="+bugtarget-portlet-tags-content",
            layer=BugsLayer)
        self.assertEqual(
            [u'tag-first', u'tag-middle', u'tag-last'],
            [tag['tag'] for tag in view.tags_cloud_data])


class BugTargetTagsMixinTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    class FakeBugTagsView(LaunchpadView, BugTargetTagsMixin):
        """A test view."""

    def test_official_tags_js_not_adaptable_to_product_or_distro(self):
        # project groups are not full bug targets so they have no tags.
        project_group = self.factory.makeProject()
        view = self.FakeBugTagsView(project_group, None)
        js = view.official_tags_js
        self.assertEqual('var official_tags = [];', js)

    def test_official_tags_js_product_without_tags(self):
        # Products without tags have an empty list.
        product = self.factory.makeProduct()
        view = self.FakeBugTagsView(product, None)
        js = view.official_tags_js
        self.assertEqual('var official_tags = [];', js)

    def test_official_tags_js_product_with_tags(self):
        # Products with tags have a list of tags.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            product.official_bug_tags = [u'cows', u'pigs', u'sheep']
        view = self.FakeBugTagsView(product, None)
        js = view.official_tags_js
        self.assertEqual('var official_tags = ["cows", "pigs", "sheep"];', js)
