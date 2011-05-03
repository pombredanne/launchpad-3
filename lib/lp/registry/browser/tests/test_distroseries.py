# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

import difflib
import re
from textwrap import TextWrapper

from BeautifulSoup import BeautifulSoup
from lxml import html
import soupmatchers
from storm.zope.interfaces import IResultSet
from testtools.content import (
    Content,
    text_content,
    )
from testtools.content_type import UTF8_TEXT
from testtools.matchers import (
    EndsWith,
    LessThan,
    Not,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import flush_database_caches
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.browser.distroseries import (
    BLACKLISTED,
    HIGHER_VERSION_THAN_PARENT,
    NON_BLACKLISTED,
    RESOLVED,
    )
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.services.features import (
    get_relevant_feature_controller,
    getFeatureFlag,
    install_feature_controller,
    )
from lp.services.features.flags import FeatureController
from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )
from lp.soyuz.enums import (
    ArchivePermissionType,
    PackagePublishingStatus,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.distributionjob import (
    IInitialiseDistroSeriesJobSource,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.testing import (
    celebrity_logged_in,
    feature_flags,
    login_person,
    person_logged_in,
    set_feature_flag,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_initialized_view


def set_derived_series_ui_feature_flag(test_case):
    # Helper to set the feature flag enabling the derived series ui.
    getFeatureStore().add(FeatureFlag(
        scope=u'default', flag=u'soyuz.derived-series-ui.enabled',
        value=u'on', priority=1))

    # XXX Michael Nelson 2010-09-21 bug=631884
    # Currently LaunchpadTestRequest doesn't set per-thread
    # features.
    def in_scope(value):
        return True
    install_feature_controller(FeatureController(in_scope))
    test_case.addCleanup(install_feature_controller, None)


class TestDistroSeriesView(TestCaseWithFactory):
    """Test the distroseries +index view."""

    layer = LaunchpadZopelessLayer

    def test_needs_linking(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        view = create_initialized_view(distroseries, '+index')
        self.assertEqual(view.needs_linking, None)

    def _createDifferenceAndGetView(self, difference_type):
        # Helper function to create a valid DSD.
        distroseries = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())
        self.factory.makeDistroSeriesDifference(
            derived_series=distroseries, difference_type=difference_type)
        return create_initialized_view(distroseries, '+index')

    def test_num_differences(self):
        diff_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS
        view = self._createDifferenceAndGetView(diff_type)
        self.assertEqual(1, view.num_differences)

    def test_num_differences_in_parent(self):
        diff_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        view = self._createDifferenceAndGetView(diff_type)
        self.assertEqual(1, view.num_differences_in_parent)

    def test_num_differences_in_child(self):
        diff_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        view = self._createDifferenceAndGetView(diff_type)
        self.assertEqual(1, view.num_differences_in_child)


class DistroSeriesIndexFunctionalTestCase(TestCaseWithFactory):
    """Test the distroseries +index page."""

    layer = DatabaseFunctionalLayer

    def _setupDifferences(self, name, parent_name, nb_diff_versions,
                          nb_diff_child, nb_diff_parent):
        # Helper to create DSD of the different types.
        derived_series = self.factory.makeDistroSeries(
            name=name,
            parent_series=self.factory.makeDistroSeries(name=parent_name))
        self.simple_user = self.factory.makePerson()
        for i in range(nb_diff_versions):
            diff_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS
            self.factory.makeDistroSeriesDifference(
                derived_series=derived_series,
                difference_type=diff_type)
        for i in range(nb_diff_child):
            diff_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
            self.factory.makeDistroSeriesDifference(
                derived_series=derived_series,
                difference_type=diff_type)
        for i in range(nb_diff_parent):
            diff_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
            self.factory.makeDistroSeriesDifference(
                derived_series=derived_series,
                difference_type=diff_type)
        return derived_series

    def test_differences_no_flag_no_portlet(self):
        # The portlet is not displayed if the feature flag is not enabled.
        derived_series = self._setupDifferences('deri', 'sid', 1, 2, 2)
        portlet_header = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Derivation portlet header', 'h2',
                text='Derived from Sid'),
            )

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                derived_series,
                '+index',
                principal=self.simple_user)
            html_content = view()

        self.assertEqual(
            None, getFeatureFlag('soyuz.derived-series-ui.enabled'))
        self.assertThat(html_content, Not(portlet_header))

    def test_differences_portlet_all_differences(self):
        # The difference portlet shows the differences with the parent
        # series.
        set_derived_series_ui_feature_flag(self)
        derived_series = self._setupDifferences('deri', 'sid', 1, 2, 3)
        portlet_display = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Derivation portlet header', 'h2',
                text='Derived from Sid'),
            soupmatchers.Tag(
                'Differences link', 'a',
                text=re.compile('\s*1 package with differences.\s*'),
                attrs={'href': re.compile('.*/\+localpackagediffs')}),
            soupmatchers.Tag(
                'Parent diffs link', 'a',
                text=re.compile('\s*2 packages in Sid.\s*'),
                attrs={'href': re.compile('.*/\+missingpackages')}),
            soupmatchers.Tag(
                'Child diffs link', 'a',
                text=re.compile('\s*3 packages in Deri.\s*'),
                attrs={'href': re.compile('.*/\+uniquepackages')}))

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                derived_series,
                '+index',
                principal=self.simple_user)
            # XXX rvb 2011-04-12 bug=758649: LaunchpadTestRequest overrides
            # self.features to NullFeatureController.
            view.request.features = get_relevant_feature_controller()
            html_content = view()

        self.assertThat(html_content, portlet_display)

    def test_differences_portlet_no_differences(self):
        # The difference portlet displays 'No differences' if there is no
        # differences with the parent.
        set_derived_series_ui_feature_flag(self)
        derived_series = self._setupDifferences('deri', 'sid', 0, 0, 0)
        portlet_display = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Derivation portlet header', 'h2',
                text='Derived from Sid'),
            soupmatchers.Tag(
                'Child diffs link', True,
                text=re.compile('\s*No differences\s*')),
              )

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                derived_series,
                '+index',
                principal=self.simple_user)
            # XXX rvb 2011-04-12 bug=758649: LaunchpadTestRequest overrides
            # self.features to NullFeatureController.
            view.request.features = get_relevant_feature_controller()
            html_content = view()

        self.assertThat(html_content, portlet_display)

    def test_differences_portlet_initialising(self):
        # The difference portlet displays 'The series is initialising.' if
        # there is an initialising job for the series.
        set_derived_series_ui_feature_flag(self)
        derived_series = self._setupDifferences('deri', 'sid', 0, 0, 0)
        job_source = getUtility(IInitialiseDistroSeriesJobSource)
        job_source.create(derived_series.parent, derived_series)
        portlet_display = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Derived series', 'h2',
                text='Derived series'),
            soupmatchers.Tag(
                'Init message', True,
                text=re.compile('\s*This series is initialising.\s*')),
              )

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                derived_series,
                '+index',
                principal=self.simple_user)
            # XXX rvb 2011-04-12 bug=758649: LaunchpadTestRequest overrides
            # self.features to NullFeatureController.
            view.request.features = get_relevant_feature_controller()
            html_content = view()

        self.assertTrue(derived_series.is_initialising)
        self.assertThat(html_content, portlet_display)


class TestMilestoneBatchNavigatorAttribute(TestCaseWithFactory):
    """Test the series.milestone_batch_navigator attribute."""

    layer = LaunchpadZopelessLayer

    def test_distroseries_milestone_batch_navigator(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        for name in ('a', 'b', 'c', 'd'):
            distroseries.newMilestone(name)
        view = create_initialized_view(distroseries, name='+index')
        self._check_milestone_batch_navigator(view)

    def test_productseries_milestone_batch_navigator(self):
        product = self.factory.makeProduct()
        for name in ('a', 'b', 'c', 'd'):
            product.development_focus.newMilestone(name)

        view = create_initialized_view(
            product.development_focus, name='+index')
        self._check_milestone_batch_navigator(view)

    def _check_milestone_batch_navigator(self, view):
        config.push('default-batch-size', """
        [launchpad]
        default_batch_size: 2
        """)
        self.assert_(
            isinstance(view.milestone_batch_navigator, BatchNavigator),
            'milestone_batch_navigator is not a BatchNavigator object: %r'
            % view.milestone_batch_navigator)
        self.assertEqual(4, view.milestone_batch_navigator.batch.total())
        expected = [
            'd',
            'c',
            ]
        milestone_names = [
            item.name
            for item in view.milestone_batch_navigator.currentBatch()]
        self.assertEqual(expected, milestone_names)
        config.pop('default-batch-size')


class TestDistroSeriesAddView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_submit(self):
        # When creating a new DistroSeries via DistroSeriesAddView, the title
        # is set to the same as the displayname (title is, in any case,
        # deprecated), the description is left empty, and parent_series is
        # None (DistroSeriesInitializeView takes care of setting that).
        user = self.factory.makePerson()
        distribution = self.factory.makeDistribution(owner=user)
        form = {
            "field.name": u"polished",
            "field.version": u"12.04",
            "field.displayname": u"Polished Polecat",
            "field.summary": u"Even The Register likes it.",
            "field.actions.create": u"Add Series",
            }
        with person_logged_in(user):
            create_initialized_view(distribution, "+addseries", form=form)
        distroseries = distribution.getSeries(u"polished")
        self.assertEqual(u"polished", distroseries.name)
        self.assertEqual(u"12.04", distroseries.version)
        self.assertEqual(u"Polished Polecat", distroseries.displayname)
        self.assertEqual(u"Polished Polecat", distroseries.title)
        self.assertEqual(u"Even The Register likes it.", distroseries.summary)
        self.assertEqual(u"", distroseries.description)
        self.assertIs(None, distroseries.parent_series)
        self.assertEqual(user, distroseries.owner)


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        self.assertTrue(view)

    def test_is_derived_series_feature_enabled(self):
        # The feature is disabled by default, but can be enabled by setting
        # the soyuz.derived-series-ui.enabled flag.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            self.assertFalse(view.is_derived_series_feature_enabled)
        with feature_flags():
            set_feature_flag(u"soyuz.derived-series-ui.enabled", u"true")
            self.assertTrue(view.is_derived_series_feature_enabled)

    def test_form_hidden_when_derived_series_feature_disabled(self):
        # The form is hidden when the feature flag is not set.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            root = html.fromstring(view())
            self.assertEqual(
                [], root.cssselect("#initseries-form-container"))
            # Instead an explanatory message is shown.
            [message] = root.cssselect("p.error.message")
            self.assertIn(
                u"The Derivative Distributions feature is under development",
                message.text)

    def test_form_shown_when_derived_series_feature_enabled(self):
        # The form is shown when the feature flag is set.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            set_feature_flag(u"soyuz.derived-series-ui.enabled", u"true")
            root = html.fromstring(view())
            self.assertNotEqual(
                [], root.cssselect("#initseries-form-container"))
            # A different explanatory message is shown for clients that don't
            # process Javascript.
            [message] = root.cssselect("p.error.message")
            self.assertIn(
                u"Javascript is required to use this page",
                message.text)
            self.assertIn(
                u"javascript-disabled",
                message.get("class").split())


class DistroSeriesDifferenceMixin:
    """A helper class for testing differences pages"""

    def _test_packagesets(self, html, packageset_text,
                          packageset_class, msg_text):
        parent_packagesets = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                msg_text, 'td',
                attrs={'class': packageset_class},
                text=packageset_text))

        self.assertThat(html, parent_packagesets)


class TestDistroSeriesLocalDifferences(
    DistroSeriesDifferenceMixin, TestCaseWithFactory):
    """Test the distroseries +localpackagediffs page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroSeriesLocalDifferences,
              self).setUp('foo.bar@canonical.com')
        set_derived_series_ui_feature_flag(self)
        self.simple_user = self.factory.makePerson()

    def test_filter_form_if_differences(self):
        # Test that the page includes the filter form if differences
        # are present
        login_person(self.simple_user)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series)

        view = create_initialized_view(
            derived_series, '+localpackagediffs', principal=self.simple_user)

        self.assertIsNot(
            None,
            find_tag_by_id(view(), 'distroseries-localdiff-search-filter'),
            "Form filter should be shown when there are differences.")

    def test_filter_noform_if_nodifferences(self):
        # Test that the page doesn't includes the filter form if no
        # differences are present
        login_person(self.simple_user)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        view = create_initialized_view(
            derived_series, '+localpackagediffs', principal=self.simple_user)

        self.assertIs(
            None,
            find_tag_by_id(view(), 'distroseries-localdiff-search-filter'),
            "Form filter should not be shown when there are no differences.")

    def test_parent_packagesets_localpackagediffs(self):
        # +localpackagediffs displays the parent packagesets.
        ds_diff = self.factory.makeDistroSeriesDifference()
        with celebrity_logged_in('admin'):
            ps = self.factory.makePackageset(
                packages=[ds_diff.source_package_name],
                distroseries=ds_diff.derived_series.parent_series)

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                ds_diff.derived_series,
                '+localpackagediffs',
                principal=self.simple_user)
            html = view()

        packageset_text = re.compile('\s*' + ps.name)
        self._test_packagesets(
            html, packageset_text, 'parent-packagesets', 'Parent packagesets')

    def test_parent_packagesets_localpackagediffs_sorts(self):
        # Multiple packagesets are sorted in a comma separated list.
        ds_diff = self.factory.makeDistroSeriesDifference()
        unsorted_names = [u"zzz", u"aaa"]
        with celebrity_logged_in('admin'):
            for name in unsorted_names:
                self.factory.makePackageset(
                    name=name,
                    packages=[ds_diff.source_package_name],
                    distroseries=ds_diff.derived_series.parent_series)

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                ds_diff.derived_series,
                '+localpackagediffs',
                principal=self.simple_user)
            html = view()

        packageset_text = re.compile(
            '\s*' + ', '.join(sorted(unsorted_names)))
        self._test_packagesets(
            html, packageset_text, 'parent-packagesets', 'Parent packagesets')

    def test_queries(self):
        # With no DistroSeriesDifferences the query count should be low and
        # fairly static. However, with some DistroSeriesDifferences the query
        # count will be higher, but it should remain the same no matter how
        # many differences there are.
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())
        ArchivePermission(
            archive=derived_series.main_archive, person=self.simple_user,
            component=getUtility(IComponentSet)["main"],
            permission=ArchivePermissionType.QUEUE_ADMIN)
        login_person(self.simple_user)

        def add_differences(num):
            for index in xrange(num):
                version = self.factory.getUniqueInteger()
                versions = {
                    'base': u'1.%d' % version,
                    'derived': u'1.%dderived1' % version,
                    'parent': u'1.%d-1' % version,
                    }
                dsd = self.factory.makeDistroSeriesDifference(
                    derived_series=derived_series,
                    versions=versions)

                # Push a base_version in... not sure how better to do it.
                removeSecurityProxy(dsd).base_version = versions["base"]

                # Add a couple of comments.
                self.factory.makeDistroSeriesDifferenceComment(dsd)
                self.factory.makeDistroSeriesDifferenceComment(dsd)

                # Update the spr, some with recipes, some with signing keys.
                # SPR.uploader references both, and the uploader is referenced
                # in the page.
                spr = dsd.source_pub.sourcepackagerelease
                if index % 2 == 0:
                    removeSecurityProxy(spr).source_package_recipe_build = (
                        self.factory.makeSourcePackageRecipeBuild(
                            sourcename=spr.sourcepackagename.name,
                            distroseries=derived_series))
                else:
                    removeSecurityProxy(spr).dscsigningkey = (
                        self.factory.makeGPGKey(owner=spr.creator))

        def flush_and_render():
            flush_database_caches()
            # Pull in the calling user's location so that it isn't recorded in
            # the query count; it causes the total to be fragile for no
            # readily apparent reason.
            self.simple_user.location
            with StormStatementRecorder() as recorder:
                view = create_initialized_view(
                    derived_series, '+localpackagediffs',
                    principal=self.simple_user)
                view()
            return recorder, view.cached_differences.batch.trueSize

        def statement_differ(rec1, rec2):
            wrapper = TextWrapper(break_long_words=False)

            def prepare_statements(rec):
                for statement in rec.statements:
                    for line in wrapper.wrap(statement):
                        yield line
                    yield "-" * wrapper.width

            def statement_diff():
                diff = difflib.ndiff(
                    list(prepare_statements(rec1)),
                    list(prepare_statements(rec2)))
                for line in diff:
                    yield "%s\n" % line

            return statement_diff

        # Render without differences and check the query count isn't silly.
        recorder1, batch_size = flush_and_render()
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.addDetail(
            "statement-count-0-differences",
            text_content(u"%d" % recorder1.count))
        # Add some differences and render.
        add_differences(2)
        recorder2, batch_size = flush_and_render()
        self.addDetail(
            "statement-count-2-differences",
            text_content(u"%d" % recorder2.count))
        # Add more differences and render again.
        add_differences(2)
        recorder3, batch_size = flush_and_render()
        self.addDetail(
            "statement-count-4-differences",
            text_content(u"%d" % recorder3.count))
        # The last render should not need more queries than the previous.
        self.addDetail(
            "statement-diff", Content(
                UTF8_TEXT, statement_differ(recorder2, recorder3)))
        # Details about the number of statements per row.
        statement_count_per_row = (
            (recorder3.count - recorder1.count) / float(batch_size))
        self.addDetail(
            "statement-count-per-row-average",
            text_content(u"%.2f" % statement_count_per_row))
        # XXX: GavinPanella 2011-04-12 bug=760733: Reducing the query count
        # further needs work. Ideally this test would be along the lines of
        # recorder3.count == recorder2.count. 4 queries above the recorder2
        # count is 2 queries per difference which is not acceptable, but is
        # *far* better than without the changes introduced by landing this.
        compromise_statement_count = recorder2.count + 4
        self.assertThat(
            recorder3, HasQueryCount(
                LessThan(compromise_statement_count + 1)))


class TestDistroSeriesLocalDifferencesZopeless(TestCaseWithFactory):
    """Test the distroseries +localpackagediffs view."""

    layer = LaunchpadZopelessLayer

    def test_view_redirects_without_feature_flag(self):
        # If the feature flag soyuz.derived-series-ui.enabled is not set the
        # view simply redirects to the derived series.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        self.assertIs(
            None, getFeatureFlag('soyuz.derived-series-ui.enabled'))
        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        response = view.request.response
        self.assertEqual(302, response.getStatus())
        self.assertEqual(
            canonical_url(derived_series), response.getHeader('location'))

    def test_label(self):
        # The view label includes the names of both series.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertEqual(
            "Source package differences between 'Derilucid' and "
            "parent series 'Lucid'",
            view.label)

    def test_batch_includes_needing_attention_only(self):
        # The differences attribute includes differences needing
        # attention only.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        current_difference = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series)
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.RESOLVED)

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertContentEqual(
            [current_difference], view.cached_differences.batch)

    def test_batch_includes_different_versions_only(self):
        # The view contains differences of type DIFFERENT_VERSIONS only.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        different_versions_diff = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series)
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            difference_type=(
                DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES))

        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertContentEqual(
            [different_versions_diff], view.cached_differences.batch)

    def test_template_includes_help_link(self):
        # The help link for popup help is included.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        set_derived_series_ui_feature_flag(self)
        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        soup = BeautifulSoup(view())
        help_links = soup.findAll(
            'a', href='/+help/soyuz/derived-series-syncing.html')
        self.assertEqual(1, len(help_links))

    def test_diff_row_includes_last_comment_only(self):
        # The most recent comment is rendered for each difference.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        difference = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series)
        difference.addComment(difference.owner, "Earlier comment")
        difference.addComment(difference.owner, "Latest comment")

        set_derived_series_ui_feature_flag(self)
        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        # Find all the rows within the body of the table
        # listing the differences.
        soup = BeautifulSoup(view())
        diff_table = soup.find('table', {'class': 'listing'})
        rows = diff_table.tbody.findAll('tr')

        self.assertEqual(1, len(rows))
        self.assertIn("Latest comment", unicode(rows[0]))
        self.assertNotIn("Earlier comment", unicode(rows[0]))

    def test_diff_row_links_to_extra_details(self):
        # The source package name links to the difference details.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        difference = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series)

        set_derived_series_ui_feature_flag(self)
        view = create_initialized_view(
            derived_series, '+localpackagediffs')
        soup = BeautifulSoup(view())
        diff_table = soup.find('table', {'class': 'listing'})
        row = diff_table.tbody.findAll('tr')[0]

        href = canonical_url(difference).replace('http://launchpad.dev', '')
        links = row.findAll('a', href=href)
        self.assertEqual(1, len(links))
        self.assertEqual(difference.source_package_name.name, links[0].string)

    def test_diff_row_shows_version_attached(self):
        # The +localpackagediffs page shows the version attached to the
        # DSD and not the last published version (bug=745776).
        package_name = 'package-1'
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        versions = {
            'base': u'1.0',
            'derived': u'1.0derived1',
            'parent': u'1.0-1',
        }
        new_version = u'1.2'

        difference = self.factory.makeDistroSeriesDifference(
            versions=versions,
            source_package_name_str=package_name,
            derived_series=derived_series)

        # Create a more recent source package publishing history.
        sourcepackagename = self.factory.getOrMakeSourcePackageName(
            package_name)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackagename,
            distroseries=derived_series,
            version=new_version)

        set_derived_series_ui_feature_flag(self)
        view = create_initialized_view(
            derived_series, '+localpackagediffs')
        soup = BeautifulSoup(view())
        diff_table = soup.find('table', {'class': 'listing'})
        row = diff_table.tbody.tr
        links = row.findAll('a', {'class': 'derived-version'})

        # The version displayed is the version attached to the
        # difference.
        self.assertEqual(1, len(links))
        self.assertEqual(versions['derived'], links[0].string.strip())

        link = canonical_url(difference.source_pub.sourcepackagerelease)
        self.assertTrue(link, EndsWith(new_version))
        # The link points to the sourcepackagerelease referenced in the
        # difference.
        self.assertTrue(
            links[0].get('href'), EndsWith(difference.source_version))

    def test_diff_row_no_published_version(self):
        # The +localpackagediffs page shows only the version (no link)
        # if we fail to fetch the published version.
        package_name = 'package-1'
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        versions = {
            'base': u'1.0',
            'derived': u'1.0derived1',
            'parent': u'1.0-1',
        }

        difference = self.factory.makeDistroSeriesDifference(
            versions=versions,
            source_package_name_str=package_name,
            derived_series=derived_series)

        # Delete the publications.
        difference.source_pub.status = PackagePublishingStatus.DELETED
        difference.parent_source_pub.status = PackagePublishingStatus.DELETED
        # Flush out the changes and invalidate caches (esp. property caches).
        flush_database_caches()

        set_derived_series_ui_feature_flag(self)
        view = create_initialized_view(
            derived_series, '+localpackagediffs')
        soup = BeautifulSoup(view())
        diff_table = soup.find('table', {'class': 'listing'})
        row = diff_table.tbody.tr

        # The table feature a simple span since we were unable to fetch a
        # published sourcepackage.
        derived_span = row.findAll('span', {'class': 'derived-version'})
        parent_span = row.findAll('span', {'class': 'parent-version'})
        self.assertEqual(1, len(derived_span))
        self.assertEqual(1, len(parent_span))

        # The versions displayed are the versions attached to the
        # difference.
        self.assertEqual(versions['derived'], derived_span[0].string.strip())
        self.assertEqual(versions['parent'], parent_span[0].string.strip())


class TestDistroSeriesLocalDifferencesFunctional(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_higher_radio_mentions_parent(self):
        set_derived_series_ui_feature_flag(self)
        parent_series = self.factory.makeDistroSeries(
            name='lucid', displayname='Lucid')
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=parent_series)
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-src-package")
        view = create_initialized_view(
            derived_series,
            '+localpackagediffs')

        radio_title = \
            "&nbsp;Blacklisted packages with a higher version than in 'Lucid'"
        radio_option_matches = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "radio displays parent's name", 'label',
                text=radio_title),
            )
        self.assertThat(view.render(), radio_option_matches)

    def _set_source_selection(self, series):
        # Set up source package format selection so that copying will
        # work with the default dsc_format used in
        # makeSourcePackageRelease.
        getUtility(ISourcePackageFormatSelectionSet).add(
            series, SourcePackageFormat.FORMAT_1_0)

    def test_batch_filtered(self):
        # The name_filter parameter allows filtering of packages by name.
        set_derived_series_ui_feature_flag(self)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        diff1 = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-src-package")
        diff2 = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-second-src-package")

        filtered_view = create_initialized_view(
            derived_series,
            '+localpackagediffs',
            query_string='field.name_filter=my-src-package')
        unfiltered_view = create_initialized_view(
            derived_series,
            '+localpackagediffs')

        self.assertContentEqual(
            [diff1], filtered_view.cached_differences.batch)
        self.assertContentEqual(
            [diff2, diff1], unfiltered_view.cached_differences.batch)

    def test_batch_non_blacklisted(self):
        # The default filter is all non blacklisted differences.
        set_derived_series_ui_feature_flag(self)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        diff1 = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-src-package")
        diff2 = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-second-src-package")
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT)

        filtered_view = create_initialized_view(
            derived_series,
            '+localpackagediffs',
            query_string='field.package_type=%s' % NON_BLACKLISTED)
        filtered_view2 = create_initialized_view(
            derived_series,
            '+localpackagediffs')

        self.assertContentEqual(
            [diff2, diff1], filtered_view.cached_differences.batch)
        self.assertContentEqual(
            [diff2, diff1], filtered_view2.cached_differences.batch)

    def test_batch_differences_packages(self):
        # field.package_type parameter allows to list only
        # blacklisted differences.
        set_derived_series_ui_feature_flag(self)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        blacklisted_diff = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT)

        blacklisted_view = create_initialized_view(
            derived_series,
            '+localpackagediffs',
            query_string='field.package_type=%s' % BLACKLISTED)
        unblacklisted_view = create_initialized_view(
            derived_series,
            '+localpackagediffs')

        self.assertContentEqual(
            [blacklisted_diff], blacklisted_view.cached_differences.batch)
        self.assertContentEqual(
            [], unblacklisted_view.cached_differences.batch)

    def test_batch_blacklisted_differences_with_higher_version(self):
        # field.package_type parameter allows to list only
        # blacklisted differences with a child's version higher than parent's.
        set_derived_series_ui_feature_flag(self)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))
        blacklisted_diff_higher = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            versions={'base': '1.1', 'parent': '1.3', 'derived': '1.10'})
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            versions={'base': '1.1', 'parent': '1.12', 'derived': '1.10'})

        blacklisted_view = create_initialized_view(
            derived_series,
            '+localpackagediffs',
            query_string='field.package_type=%s' % HIGHER_VERSION_THAN_PARENT)
        unblacklisted_view = create_initialized_view(
            derived_series,
            '+localpackagediffs')

        self.assertContentEqual(
            [blacklisted_diff_higher],
            blacklisted_view.cached_differences.batch)
        self.assertContentEqual(
            [], unblacklisted_view.cached_differences.batch)

    def test_batch_resolved_differences(self):
        # Test that we can search for differences that we marked
        # resolved.
        set_derived_series_ui_feature_flag(self)
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-src-package")
        self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            source_package_name_str="my-second-src-package")
        resolved_diff = self.factory.makeDistroSeriesDifference(
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.RESOLVED)

        filtered_view = create_initialized_view(
            derived_series,
            '+localpackagediffs',
            query_string='field.package_type=%s' % RESOLVED)

        self.assertContentEqual(
            [resolved_diff], filtered_view.cached_differences.batch)

    def _setUpDSD(self, src_name='src-name', versions=None,
                  difference_type=None):
        # Helper to create a derived series with fixed names and proper
        # source package format selection along with a DSD.
        parent_series = self.factory.makeDistroSeries(name='warty')
        derived_series = self.factory.makeDistroSeries(
            distribution=self.factory.makeDistribution(name='deribuntu'),
            name='derilucid', parent_series=parent_series)
        self._set_source_selection(derived_series)
        self.factory.makeDistroSeriesDifference(
            source_package_name_str=src_name,
            derived_series=derived_series, versions=versions,
            difference_type=difference_type)
        sourcepackagename = self.factory.getOrMakeSourcePackageName(
            src_name)
        set_derived_series_ui_feature_flag(self)
        return derived_series, parent_series, sourcepackagename

    def test_canPerformSync_anon(self):
        # Anonymous users cannot sync packages.
        derived_series, _, _ = self._setUpDSD()
        view = create_initialized_view(
            derived_series, '+localpackagediffs')

        self.assertFalse(view.canPerformSync())

    def test_canPerformSync_non_anon_no_perm_dest_archive(self):
        # Logged-in users with no permission on the destination archive
        # are not presented with options to perform syncs.
        derived_series, _, _ = self._setUpDSD()
        with person_logged_in(self.factory.makePerson()):
            view = create_initialized_view(
                derived_series, '+localpackagediffs')

            self.assertFalse(view.canPerformSync())

    def _setUpPersonWithPerm(self, derived_series):
        # Helper to create a person with an upload permission on the
        # series' archive.
        person = self.factory.makePerson()
        ArchivePermission(
            archive=derived_series.main_archive, person=person,
            component=getUtility(IComponentSet)["main"],
            permission=ArchivePermissionType.QUEUE_ADMIN)
        return person

    def test_canPerformSync_non_anon(self):
        # Logged-in users with a permission on the destination archive
        # are presented with options to perform syncs.
        # Note that a more fine-grained perm check is done on each
        # synced package.
        derived_series, _, _ = self._setUpDSD()
        person = self._setUpPersonWithPerm(derived_series)
        with person_logged_in(person):
            view = create_initialized_view(
                derived_series, '+localpackagediffs')

            self.assertTrue(view.canPerformSync())

    def _syncAndGetView(self, derived_series, person, sync_differences,
                        difference_type=None, view_name='+localpackagediffs'):
        # A helper to get the POST'ed sync view.
        with person_logged_in(person):
            view = create_initialized_view(
                derived_series, view_name,
                method='POST', form={
                    'field.selected_differences': sync_differences,
                    'field.actions.sync': 'Sync',
                    })
            return view

    def test_sync_error_nothing_selected(self):
        # An error is raised when a sync is requested without any selection.
        derived_series, _, _ = self._setUpDSD()
        person = self._setUpPersonWithPerm(derived_series)
        view = self._syncAndGetView(derived_series, person, [])

        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'No differences selected.', view.errors[0])

    def test_sync_error_invalid_selection(self):
        # An error is raised when an invalid difference is selected.
        derived_series, _, _ = self._setUpDSD('my-src-name')
        person = self._setUpPersonWithPerm(derived_series)
        view = self._syncAndGetView(
            derived_series, person, ['some-other-name'])

        self.assertEqual(2, len(view.errors))
        self.assertEqual(
            'No differences selected.', view.errors[0])
        self.assertEqual(
            'Invalid value', view.errors[1].error_name)

    def test_sync_error_no_perm_dest_archive(self):
        # A user without upload rights on the destination archive cannot
        # sync packages.
        derived_series, _, _ = self._setUpDSD('my-src-name')
        person = self._setUpPersonWithPerm(derived_series)
        view = self._syncAndGetView(
            derived_series, person, ['my-src-name'])

        self.assertEqual(1, len(view.errors))
        self.assertTrue(
            "The signer of this package has no upload rights to this "
            "distribution's primary archive" in view.errors[0])

    def makePersonWithComponentPermission(self, archive, component=None):
        person = self.factory.makePerson()
        if component is None:
            component = self.factory.makeComponent()
        removeSecurityProxy(archive).newComponentUploader(
            person, component)
        return person, component

    def test_sync_success_perm_component(self):
        # A user with upload rights on the destination component
        # can sync packages.
        derived_series, parent_series, sourcepackagename = self._setUpDSD(
            'my-src-name')
        person, _ = self.makePersonWithComponentPermission(
            derived_series.main_archive,
            derived_series.getSourcePackage(
                sourcepackagename).latest_published_component)
        view = self._syncAndGetView(
            derived_series, person, ['my-src-name'])

        self.assertEqual(0, len(view.errors))

    def test_sync_error_no_perm_component(self):
        # A user without upload rights on the destination component
        # will get an error when he syncs packages to this component.
        derived_series, parent_series, sourcepackagename = self._setUpDSD(
            'my-src-name')
        person, another_component = self.makePersonWithComponentPermission(
            derived_series.main_archive)
        view = self._syncAndGetView(
            derived_series, person, ['my-src-name'])

        self.assertEqual(1, len(view.errors))
        self.assertTrue(
            "Signer is not permitted to upload to the "
            "component" in view.errors[0])

    def test_sync_notification_on_success(self):
        # A user with upload rights on the destination archive can
        # sync packages. Notifications about the synced packages are
        # displayed and the packages are copied inside the destination
        # series.
        versions = {
            'base': '1.0',
            'derived': '1.0derived1',
            'parent': '1.0-1',
        }
        derived_series, parent_series, sourcepackagename = self._setUpDSD(
            'my-src-name', versions=versions)

        # Setup a user with upload rights.
        person = self.factory.makePerson()
        removeSecurityProxy(derived_series.main_archive).newPackageUploader(
            person, sourcepackagename)

        # The inital state is that 1.0-1 is not in the derived series.
        pubs = derived_series.main_archive.getPublishedSources(
            name='my-src-name', version=versions['parent'],
            distroseries=derived_series).any()
        self.assertIs(None, pubs)

        # Now, sync the source from the parent using the form.
        view = self._syncAndGetView(
            derived_series, person, ['my-src-name'])

        # The parent's version should now be in the derived series:
        pub = derived_series.main_archive.getPublishedSources(
            name='my-src-name', version=versions['parent'],
            distroseries=derived_series).one()
        self.assertIsNot(None, pub)
        self.assertEqual(versions['parent'], pub.sourcepackagerelease.version)

        # The view should show no errors, and the notification should
        # confirm the sync worked.
        self.assertEqual(0, len(view.errors))
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            '<p>Packages copied to '
            '<a href="http://launchpad.dev/deribuntu/derilucid"'
            '>Derilucid</a>:</p>\n<ul>\n<li>my-src-name 1.0-1 in '
            'derilucid</li>\n</ul>',
            notifications[0].message)
        # 302 is a redirect back to the same page.
        self.assertEqual(302, view.request.response.getStatus())

    def test_sync_success_not_yet_in_derived_series(self):
        # If the package to sync does not exist yet in the derived series,
        # upload right to any component inside the destination series will be
        # enough to sync the package.
        versions = {
            'parent': '1.0-1',
        }
        missing = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        derived_series, parent_series, sourcepackagename = self._setUpDSD(
            'my-src-name', difference_type=missing, versions=versions)
        person, another_component = self.makePersonWithComponentPermission(
            derived_series.main_archive)
        view = self._syncAndGetView(
            derived_series, person, ['my-src-name'],
            view_name='+missingpackages')

        self.assertEqual(0, len(view.errors))
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            '<p>Packages copied to '
            '<a href="http://launchpad.dev/deribuntu/derilucid"'
            '>Derilucid</a>:</p>\n<ul>\n<li>my-src-name 1.0-1 in '
            'derilucid</li>\n</ul>',
            notifications[0].message)


class TestDistroSeriesNeedsPackagesView(TestCaseWithFactory):
    """Test the distroseries +needs-packaging view."""

    layer = LaunchpadZopelessLayer

    def test_cached_unlinked_packages(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        distroseries = self.factory.makeDistroSeries(distribution=ubuntu)
        view = create_initialized_view(distroseries, '+needs-packaging')
        self.assertTrue(
            IResultSet.providedBy(
                view.cached_unlinked_packages.currentBatch().list),
            '%s should batch IResultSet so that slicing will limit the '
            'query' % view.cached_unlinked_packages.currentBatch().list)


class DistroSeriesMissingPackageDiffsTestCase(TestCaseWithFactory):
    """Test the distroseries +missingpackages view."""

    layer = LaunchpadZopelessLayer

    def test_missingpackages_differences(self):
        # The view fetches the differences with type
        # MISSING_FROM_DERIVED_SERIES.
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

        missing_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        # Missing blacklisted diff.
        self.factory.makeDistroSeriesDifference(
            difference_type=missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT)

        missing_diff = self.factory.makeDistroSeriesDifference(
            difference_type=missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION)

        view = create_initialized_view(
            derived_series, '+missingpackages')

        self.assertContentEqual(
            [missing_diff], view.cached_differences.batch)

    def test_missingpackages_differences_empty(self):
        # The view is empty if there is no differences with type
        # MISSING_FROM_DERIVED_SERIES.
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

        not_missing_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        # Missing diff.
        self.factory.makeDistroSeriesDifference(
            difference_type=not_missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION)

        view = create_initialized_view(
            derived_series, '+missingpackages')

        self.assertContentEqual(
            [], view.cached_differences.batch)


class DistroSeriesMissingPackagesPageTestCase(DistroSeriesDifferenceMixin,
                                              TestCaseWithFactory):
    """Test the distroseries +missingpackages page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(DistroSeriesMissingPackagesPageTestCase,
              self).setUp('foo.bar@canonical.com')
        set_derived_series_ui_feature_flag(self)
        self.simple_user = self.factory.makePerson()

    def test_parent_packagesets_missingpackages(self):
        # +missingpackages displays the packagesets in the parent.
        missing_type = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        self.ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=missing_type)

        with celebrity_logged_in('admin'):
            ps = self.factory.makePackageset(
                packages=[self.ds_diff.source_package_name],
                distroseries=self.ds_diff.derived_series.parent_series)

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                self.ds_diff.derived_series,
                '+missingpackages',
                principal=self.simple_user)
            html = view()

        packageset_text = re.compile('\s*' + ps.name)
        self._test_packagesets(
            html, packageset_text, 'parent-packagesets', 'Parent packagesets')


class DistroSerieUniquePackageDiffsTestCase(TestCaseWithFactory):
    """Test the distroseries +uniquepackages view."""

    layer = LaunchpadZopelessLayer

    def test_uniquepackages_differences(self):
        # The view fetches the differences with type
        # UNIQUE_TO_DERIVED_SERIES.
        derived_series = self.factory.makeDistroSeries(
            name='derilucid', parent_series=self.factory.makeDistroSeries(
                name='lucid'))

        missing_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        # Missing blacklisted diff.
        self.factory.makeDistroSeriesDifference(
            difference_type=missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT)

        missing_diff = self.factory.makeDistroSeriesDifference(
            difference_type=missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION)

        view = create_initialized_view(
            derived_series, '+uniquepackages')

        self.assertContentEqual(
            [missing_diff], view.cached_differences.batch)

    def test_uniquepackages_differences_empty(self):
        # The view is empty if there is no differences with type
        # UNIQUE_TO_DERIVED_SERIES.
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

        not_missing_type = DistroSeriesDifferenceType.DIFFERENT_VERSIONS

        # Missing diff.
        self.factory.makeDistroSeriesDifference(
            difference_type=not_missing_type,
            derived_series=derived_series,
            status=DistroSeriesDifferenceStatus.NEEDS_ATTENTION)

        view = create_initialized_view(
            derived_series, '+uniquepackages')

        self.assertContentEqual(
            [], view.cached_differences.batch)


class DistroSeriesUniquePackagesPageTestCase(DistroSeriesDifferenceMixin,
                                             TestCaseWithFactory):
    """Test the distroseries +uniquepackages page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(DistroSeriesUniquePackagesPageTestCase,
              self).setUp('foo.bar@canonical.com')
        set_derived_series_ui_feature_flag(self)
        self.simple_user = self.factory.makePerson()

    def test_packagesets_uniquepackages(self):
        # +uniquepackages displays the packagesets in the parent.
        missing_type = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        self.ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=missing_type)

        with celebrity_logged_in('admin'):
            ps = self.factory.makePackageset(
                packages=[self.ds_diff.source_package_name],
                distroseries=self.ds_diff.derived_series)

        with person_logged_in(self.simple_user):
            view = create_initialized_view(
                self.ds_diff.derived_series,
                '+uniquepackages',
                principal=self.simple_user)
            html = view()

        packageset_text = re.compile('\s*' + ps.name)
        self._test_packagesets(
            html, packageset_text, 'packagesets', 'Packagesets')
