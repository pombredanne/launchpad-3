# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
from soupmatchers import (
    HTMLContains,
    Tag,
    )
from storm.expr import LeftJoin
from storm.store import Store
from testtools.matchers import (
    Equals,
    Not,
    )
from zope.component import getUtility

from canonical.launchpad.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    find_tags_by_class,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.model.bugtask import BugTask
from lp.registry.model.person import Person
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    BrowserTestCase,
    login_person,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.views import (
    create_view,
    create_initialized_view,
    )


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
            test-dsp in Test-distro does not use Launchpad for bug tracking.
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
        self.factory.makeDistroSeries(distribution=distro, name='test-series')
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

    def test_searchUnbatched_can_preload_objects(self):
        # BugTaskSearchListingView.searchUnbatched() can optionally
        # preload objects while retrieving the bugtasks.
        product = self.factory.makeProduct()
        bugtask_1 = self.factory.makeBug(product=product).default_bugtask
        bugtask_2 = self.factory.makeBug(product=product).default_bugtask
        view = create_initialized_view(product, '+bugs')
        Store.of(product).invalidate()
        with StormStatementRecorder() as recorder:
            prejoins = [
                (Person, LeftJoin(Person, BugTask.owner == Person.id)),
                ]
            bugtasks = list(view.searchUnbatched(prejoins=prejoins))
            self.assertEqual(
                [bugtask_1, bugtask_2], bugtasks)
            # If the table prejoin failed, then this will issue two
            # additional SQL queries
            [bugtask.owner for bugtask in bugtasks]
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_search_components_error(self):
        # Searching for using components for bug targets that are not a distro
        # or distroseries will report an error, but not OOPS.  See bug
        # 838957.
        product = self.factory.makeProduct()
        form = {
            'search': 'Search',
            'advanced': 1,
            'field.component': 1,
            'field.component-empty-marker': 1}
        with person_logged_in(product.owner):
            view = create_initialized_view(product, '+bugs', form=form)
            view.searchUnbatched()
        response = view.request.response
        self.assertEqual(1, len(response.notifications))
        expected = (
            "Search by component requires a context with "
            "a distribution or distroseries.")
        self.assertEqual(expected, response.notifications[0].message)
        self.assertEqual(
            canonical_url(product, rootsite='bugs', view_name='+bugs'),
            response.getHeader('Location'))

    def test_non_batch_template(self):
        # The correct template is used for non batch requests.
        product = self.factory.makeProduct()
        form = {'search': 'Search'}
        view = create_view(product, '+bugs', form=form)
        self.assertEqual(
            'buglisting-default.pt', os.path.basename(view.template.filename))

    def test_batch_template(self):
        # The correct template is used for batch requests.
        product = self.factory.makeProduct()
        form = {'search': 'Search'}
        view = create_view(
            product, '+bugs', form=form, query_string='batch_request=True')
        self.assertEqual(
            view.bugtask_table_template.filename, view.template.filename)

    def test_search_batch_request(self):
        # A search request with a 'batch_request' query parameter causes the
        # view to just render the next batch of results.
        product = self.factory.makeProduct()
        form = {'search': 'Search'}
        view = create_initialized_view(
            product, '+bugs', form=form, query_string='batch_request=True')
        content = view()
        self.assertIsNone(find_main_content(content))
        self.assertIsNotNone(
            find_tag_by_id(content, 'bugs-batch-links-upper'))

    def test_ajax_batch_navigation_feature_flag(self):
        # The Javascript to wire up the ajax batch navigation behavior is
        # correctly hidden behind a feature flag.
        product = self.factory.makeProduct()
        form = {'search': 'Search'}
        with person_logged_in(product.owner):
            product.official_malone = True
        flags = {u"ajax.batch_navigator.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs', form=form)
            self.assertTrue(
                'Y.lp.app.batchnavigator.BatchNavigatorHooks' in view())
        view = create_initialized_view(product, '+bugs', form=form)
        self.assertFalse(
            'Y.lp.app.batchnavigator.BatchNavigatorHooks' in view())

    def test_dynamic_bug_listing_feature_flag(self):
        # BugTaskSearchListingView.dynamic_bug_listing_enabled provides
        # access to the feature flag bugs.dynamic_bug_listings.enabled.
        # The property is False by default.
        product = self.factory.makeProduct()
        view = create_initialized_view(product, '+bugs')
        self.assertFalse(view.dynamic_bug_listing_enabled)
        # When the feature flag is turned on, dynamic_bug_listing_enabled
        # is True.
        flags = {u"bugs.dynamic_bug_listings.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs')
            self.assertTrue(view.dynamic_bug_listing_enabled)

    def test_search_macro_title(self):
        # BugTaskSearchListingView.dynamic_bug_listing_enabled returns
        # the title text for the macro `simple-search-form`.
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        view = create_initialized_view(product, '+bugs')
        self.assertEqual(
            'Search bugs in Test Product', view.search_macro_title)

        # The title not shown by default.
        form_title_matches = Tag(
            'Search form title', 'h3', text=view.search_macro_title)
        self.assertThat(view.render(), Not(HTMLContains(form_title_matches)))

        # If the feature flag bugs.dynamic_bug_listings.enabled
        # is set, the title is shown.
        flags = {u"bugs.dynamic_bug_listings.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs')
            self.assertThat(view.render(), HTMLContains(form_title_matches))

    def test_search_macro_sort_widget_hidden_for_dynamic_bug_listing(self):
        # The macro `simple-search-form` has by default a sort widget.
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        view = create_initialized_view(product, '+bugs')
        sort_selector_matches = Tag(
            'Sort widget found', tag_type='select', attrs={'id': 'orderby'})
        self.assertThat(view.render(), HTMLContains(sort_selector_matches))

        # If the feature flag bugs.dynamic_bug_listings.enabled
        # is set, the sort widget is not rendered.
        flags = {u"bugs.dynamic_bug_listings.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs')
            self.assertThat(
                view.render(), Not(HTMLContains(sort_selector_matches)))

    def test_search_macro_div_node_no_css_class_by_default(self):
        # The <div> enclosing the search form in the macro
        # `simple-search-form` has by default no CSS class.
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        view = create_initialized_view(product, '+bugs')
        # The <div> node exists.
        rendered_view = view.render()
        search_div_matches = Tag(
            'Main search div', tag_type='div',
            attrs={'id': 'bugs-search-form'})
        self.assertThat(
            rendered_view, HTMLContains(search_div_matches))
        # But it has no 'class' attribute.
        attributes = {
            'id': 'bugs-search-form',
            'class': True,
            }
        search_div_with_class_attribute_matches = Tag(
            'Main search div', tag_type='div', attrs=attributes)
        self.assertThat(
            rendered_view,
            HTMLContains(Not(search_div_with_class_attribute_matches)))

    def test_search_macro_div_node_with_css_class_for_dynamic_listings(self):
        # If the feature flag bugs.dynamic_bug_listings.enabled
        # is set, the <div> node has the CSS class "dynamic_bug_listing".
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        attributes = {
            'id': 'bugs-search-form',
            'class': 'dynamic_bug_listing',
            }
        search_div_with_class_attribute_matches = Tag(
            'Main search div feature flag bugs.dynamic_bug_listings.enabled',
            tag_type='div', attrs=attributes)
        flags = {u"bugs.dynamic_bug_listings.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs')
            self.assertThat(
                view.render(),
                HTMLContains(search_div_with_class_attribute_matches))

    def test_search_macro_css_for_form_node_default(self):
        # The <form> node of the search form in the macro
        # `simple-search-form` has by default the CSS classes
        # 'prmary search'
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        view = create_initialized_view(product, '+bugs')
        # The <div> node exists.
        rendered_view = view.render()
        attributes = {
            'name': 'search',
            'class': 'primary search',
            }
        search_form_matches = Tag(
            'Default search form CSS classes', tag_type='form',
            attrs=attributes)
        self.assertThat(
            rendered_view, HTMLContains(search_form_matches))

    def test_search_macro_css_for_form_node_with_dynamic_bug_listings(self):
        # If the feature flag bugs.dynamic_bug_listings.enabled
        # is set, the <form> node has the CSS classes
        # "primary search dynamic_bug_listing".
        product = self.factory.makeProduct(
            displayname='Test Product', official_malone=True)
        attributes = {
            'name': 'search',
            'class': 'primary search dynamic_bug_listing',
            }
        search_form_matches = Tag(
            'Search form CSS classes with feature flag '
            'bugs.dynamic_bug_listings.enabled', tag_type='form',
            attrs=attributes)
        flags = {u"bugs.dynamic_bug_listings.enabled": u"true"}
        with FeatureFixture(flags):
            view = create_initialized_view(product, '+bugs')
            self.assertThat(view.render(), HTMLContains(search_form_matches))


class BugTargetTestCase(TestCaseWithFactory):
    """Test helpers for setting up `IBugTarget` tests."""

    def _makeBugTargetProduct(self, bug_tracker=None, packaging=False):
        """Return a product that may use Launchpad or an external bug tracker.

        bug_tracker may be None, 'launchpad', or 'external'.
        """
        product = self.factory.makeProduct()
        if bug_tracker is not None:
            with person_logged_in(product.owner):
                if bug_tracker == 'launchpad':
                    product.official_malone = True
                else:
                    product.bugtracker = self.factory.makeBugTracker()
        if packaging:
            self.factory.makePackagingLink(
                productseries=product.development_focus, in_ubuntu=True)
        return product


class TestBugTaskSearchListingViewProduct(BugTargetTestCase):

    layer = DatabaseFunctionalLayer

    def test_external_bugtracker_is_none(self):
        bug_target = self._makeBugTargetProduct()
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(None, view.external_bugtracker)

    def test_external_bugtracker(self):
        bug_target = self._makeBugTargetProduct(bug_tracker='external')
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(bug_target.bugtracker, view.external_bugtracker)

    def test_has_bugtracker_is_false(self):
        bug_target = self.factory.makeProduct()
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(False, view.has_bugtracker)

    def test_has_bugtracker_external_is_true(self):
        bug_target = self._makeBugTargetProduct(bug_tracker='external')
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(True, view.has_bugtracker)

    def test_has_bugtracker_launchpad_is_true(self):
        bug_target = self._makeBugTargetProduct(bug_tracker='launchpad')
        view = create_initialized_view(bug_target, '+bugs')
        self.assertEqual(True, view.has_bugtracker)

    def test_product_without_packaging_also_in_ubuntu_is_none(self):
        bug_target = self._makeBugTargetProduct(bug_tracker='launchpad')
        login_person(bug_target.owner)
        view = create_initialized_view(
            bug_target, '+bugs', principal=bug_target.owner)
        self.assertEqual(None, find_tag_by_id(view(), 'also-in-ubuntu'))

    def test_product_with_packaging_also_in_ubuntu(self):
        bug_target = self._makeBugTargetProduct(
            bug_tracker='launchpad', packaging=True)
        login_person(bug_target.owner)
        view = create_initialized_view(
            bug_target, '+bugs', principal=bug_target.owner)
        content = find_tag_by_id(view.render(), 'also-in-ubuntu')
        link = canonical_url(
            bug_target.ubuntu_packages[0], force_local_path=True)
        self.assertEqual(link, content.a['href'])

    def test_ask_question_does_not_use_launchpad(self):
        bug_target = self._makeBugTargetProduct(
            bug_tracker='launchpad', packaging=True)
        login_person(bug_target.owner)
        bug_target.official_answers = False
        view = create_initialized_view(
            bug_target, '+bugs', principal=bug_target.owner)
        self.assertEqual(None, view.addquestion_url)

    def test_ask_question_uses_launchpad(self):
        bug_target = self._makeBugTargetProduct(
            bug_tracker='launchpad', packaging=True)
        login_person(bug_target.owner)
        bug_target.official_answers = True
        view = create_initialized_view(
            bug_target, '+bugs', principal=bug_target.owner)
        url = canonical_url(
            bug_target, rootsite='answers', view_name='+addquestion')
        self.assertEqual(url, view.addquestion_url)


class TestBugTaskSearchListingViewDSP(BugTargetTestCase):

    layer = DatabaseFunctionalLayer

    def _getBugTarget(self, obj):
        """Return the `IBugTarget` under test.

        Return the object that was passed. Sub-classes can redefine
        this method.
        """
        return obj

    def test_package_with_upstream_launchpad_project(self):
        upstream_project = self._makeBugTargetProduct(
            bug_tracker='launchpad', packaging=True)
        login_person(upstream_project.owner)
        bug_target = self._getBugTarget(
            upstream_project.distrosourcepackages[0])
        view = create_initialized_view(
            bug_target, '+bugs', principal=upstream_project.owner)
        self.assertEqual(upstream_project, view.upstream_launchpad_project)
        content = find_tag_by_id(view.render(), 'also-in-upstream')
        link = canonical_url(upstream_project, rootsite='bugs')
        self.assertEqual(link, content.a['href'])

    def test_package_with_upstream_nonlaunchpad_project(self):
        upstream_project = self._makeBugTargetProduct(packaging=True)
        login_person(upstream_project.owner)
        bug_target = self._getBugTarget(
            upstream_project.distrosourcepackages[0])
        view = create_initialized_view(
            bug_target, '+bugs', principal=upstream_project.owner)
        self.assertEqual(None, view.upstream_launchpad_project)
        self.assertEqual(None, find_tag_by_id(view(), 'also-in-upstream'))

    def test_package_without_upstream_project(self):
        observer = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage(
            'test-dsp', distribution=getUtility(ILaunchpadCelebrities).ubuntu)
        bug_target = self._getBugTarget(dsp)
        login_person(observer)
        view = create_initialized_view(
            bug_target, '+bugs', principal=observer)
        self.assertEqual(None, view.upstream_launchpad_project)
        self.assertEqual(None, find_tag_by_id(view(), 'also-in-upstream'))


class TestBugTaskSearchListingViewSP(TestBugTaskSearchListingViewDSP):

        def _getBugTarget(self, dsp):
            """Return the current `ISourcePackage` for the dsp."""
            return dsp.development_version
