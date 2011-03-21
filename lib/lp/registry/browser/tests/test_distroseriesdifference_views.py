# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the DistroSeriesDifference views."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from zope.component import getUtility

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.browser.distroseriesdifference import (
    DistroSeriesDifferenceDisplayComment,
    )
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource)
from lp.services.comments.interfaces.conversation import (
    IComment,
    IConversation,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_provides_conversation(self):
        # The DSDView provides a conversation implementation.
        ds_diff = self.factory.makeDistroSeriesDifference()

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        self.assertTrue(verifyObject(IConversation, view))

    def test_comment_for_display_provides_icomment(self):
        # The DSDDisplayComment browser object provides IComment.
        ds_diff = self.factory.makeDistroSeriesDifference()
        owner = ds_diff.derived_series.owner
        with person_logged_in(owner):
            comment = ds_diff.addComment(owner, "I'm working on this.")
        comment_for_display = DistroSeriesDifferenceDisplayComment(comment)

        self.assertTrue(verifyObject(IComment, comment_for_display))

    def addSummaryToDifference(self, distro_series_difference):
        """Helper that adds binaries with summary info to the source pubs."""
        # Avoid circular import.
        from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
        distro_series = distro_series_difference.derived_series
        source_package_name_str = (
            distro_series_difference.source_package_name.name)
        stp = SoyuzTestPublisher()

        if distro_series_difference.difference_type == (
            DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES):
            source_pub = distro_series_difference.parent_source_pub
        else:
            source_pub = distro_series_difference.source_pub

        stp.makeSourcePackageSummaryData(source_pub)
        stp.updateDistroSeriesPackageCache(source_pub.distroseries)

        # updateDistroSeriesPackageCache reconnects the db, so the
        # objects need to be reloaded.
        dsd_source = getUtility(IDistroSeriesDifferenceSource)
        ds_diff = dsd_source.getByDistroSeriesAndName(
            distro_series, source_package_name_str)
        return ds_diff

    def test_binary_summaries_for_source_pub(self):
        # For packages unique to the derived series (or different
        # versions) the summary is based on the derived source pub.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_diff = self.addSummaryToDifference(ds_diff)

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertIsNot(None, view.binary_summaries)
        self.assertEqual([
            u'flubber-bin: summary for flubber-bin',
            u'flubber-lib: summary for flubber-lib',
            ], view.binary_summaries)

    def test_binary_summaries_for_missing_difference(self):
        # For packages only in the parent series, the summary is based
        # on the parent publication.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=(
                DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))
        ds_diff = self.addSummaryToDifference(ds_diff)

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertIsNot(None, view.binary_summaries)
        self.assertEqual([
            u'flubber-bin: summary for flubber-bin',
            u'flubber-lib: summary for flubber-lib',
            ], view.binary_summaries)

    def test_binary_summaries_no_pubs(self):
        # If the difference has been resolved by removing packages then
        # there will not be a summary.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=(
                DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))
        with celebrity_logged_in('admin'):
            ds_diff.parent_source_pub.status = PackagePublishingStatus.DELETED
        ds_diff.update()

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertIs(None, ds_diff.parent_source_pub)
        self.assertIs(None, ds_diff.source_pub)
        self.assertIs(None, view.binary_summaries)

    def test_show_edit_options_non_ajax(self):
        # Blacklist options are not shown for non-ajax requests.
        ds_diff = self.factory.makeDistroSeriesDifference()

        # Without JS, even editors don't see blacklist options.
        with person_logged_in(ds_diff.owner):
            view = create_initialized_view(
                ds_diff, '+listing-distroseries-extra')
        self.assertFalse(view.show_edit_options)

    def test_show_edit_options_editor(self):
        # Blacklist options are shown if requested by an editor via
        # ajax.
        ds_diff = self.factory.makeDistroSeriesDifference()

        request = LaunchpadTestRequest(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        with person_logged_in(ds_diff.owner):
            view = create_initialized_view(
                ds_diff, '+listing-distroseries-extra', request=request)
            self.assertTrue(view.show_edit_options)

    def test_show_edit_options_non_editor(self):
        # Even with a JS request, non-editors do not see the options.
        ds_diff = self.factory.makeDistroSeriesDifference()

        request = LaunchpadTestRequest(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        view = create_initialized_view(
            ds_diff, '+listing-distroseries-extra', request=request)
        self.assertFalse(view.show_edit_options)


class DistroSeriesDifferenceTemplateTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def number_of_request_diff_texts(self, html):
        """Check that the html doesn't include the request diff text."""
        soup = BeautifulSoup(html)
        return len(soup.findAll('li', 'request-derived-diff'))

    def contains_one_link_to_diff(self, html, package_diff):
        """Return whether the html contains a link to the diff content."""
        soup = BeautifulSoup(html)
        return 1 == len(soup.findAll(
            'a', href=package_diff.diff_content.http_url))

    def test_both_request_diff_texts_rendered(self):
        # An unlinked description of a potential diff is displayed when
        # no diff is present.
        ds_diff = self.factory.makeDistroSeriesDifference()

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        # Both diffs present simple text repr. of proposed diff.
        self.assertEqual(2, self.number_of_request_diff_texts(view()))

    def test_source_diff_rendering_diff(self):
        # A linked description of the diff is displayed when
        # it is present.
        ds_diff = self.factory.makeDistroSeriesDifference()

        with person_logged_in(ds_diff.derived_series.owner):
            ds_diff.package_diff = self.factory.makePackageDiff()

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        # The text for the parent diff remains, but the source package
        # diff is now a link.
        self.assertEqual(1, self.number_of_request_diff_texts(view()))
        self.assertTrue(
            self.contains_one_link_to_diff(view(), ds_diff.package_diff))

    def test_source_diff_rendering_no_source(self):
        # If there is no source pub for this difference, then we don't
        # display even the request for a diff.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=
                (DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        self.assertEqual(1, self.number_of_request_diff_texts(view()))

    def test_parent_source_diff_rendering_diff(self):
        # A linked description of the diff is displayed when
        # it is present.
        ds_diff = self.factory.makeDistroSeriesDifference()

        with person_logged_in(ds_diff.derived_series.owner):
            ds_diff.parent_package_diff = self.factory.makePackageDiff()

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        # The text for the source diff remains, but the parent package
        # diff is now a link.
        self.assertEqual(1, self.number_of_request_diff_texts(view()))
        self.assertTrue(
            self.contains_one_link_to_diff(
                view(), ds_diff.parent_package_diff))

    def test_parent_source_diff_rendering_no_source(self):
        # If there is no source pub for this difference, then we don't
        # display even the request for a diff.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=
                (DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES))

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        self.assertEqual(1, self.number_of_request_diff_texts(view()))

    def test_comments_rendered(self):
        # If there are comments on the difference, they are rendered.
        ds_diff = self.factory.makeDistroSeriesDifference()
        owner = ds_diff.derived_series.owner
        with person_logged_in(owner):
            ds_diff.addComment(owner, "I'm working on this.")
            ds_diff.addComment(owner, "Here's another comment.")

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')
        soup = BeautifulSoup(view())

        self.assertEqual(
            1, len(soup.findAll('pre', text="I'm working on this.")))
        self.assertEqual(
            1, len(soup.findAll('pre', text="Here's another comment.")))

    def test_blacklist_options(self):
        # blacklist options are presented to editors.
        ds_diff = self.factory.makeDistroSeriesDifference()

        with person_logged_in(ds_diff.owner):
            request = LaunchpadTestRequest(
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            view = create_initialized_view(
                ds_diff, '+listing-distroseries-extra', request=request)
            soup = BeautifulSoup(view())

        self.assertEqual(
            1, len(soup.findAll('div', {'class': 'blacklist-options'})))

    def test_blacklist_options_initial_values_none(self):
        ds_diff = self.factory.makeDistroSeriesDifference()
        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        # If the difference is not currently blacklisted, 'NONE' is set
        # as the default value for the field.
        self.assertEqual('NONE', view.initial_values.get('blacklist_options'))

    def test_blacklist_options_initial_values_current(self):
        ds_diff = self.factory.makeDistroSeriesDifference(
            status=DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT)
        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertEqual(
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            view.initial_values.get('blacklist_options'))

    def test_blacklist_options_initial_values_always(self):
        ds_diff = self.factory.makeDistroSeriesDifference(
            status=DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS)
        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertEqual(
            DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS,
            view.initial_values.get('blacklist_options'))
