# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the DistroSeriesDifference views."""

from __future__ import with_statement

__metaclass__ = type

from zope.component import getUtility

from canonical.testing import DatabaseFunctionalLayer
from lp.registry.enum import DistroSeriesDifferenceType
from lp.registry.interfaces.distroseriesdifference import IDistroSeriesDifferenceSource
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def addSummaryToDifference(self, distro_series_difference):
        """Helper that adds binaries with summary info to the source pubs."""
        distro_series = distro_series_difference.derived_series
        source_package_name_str = distro_series_difference.source_package_name.name
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

    def test_summary_for_source_pub(self):
        # For packages unique to the derived series (or different
        # versions) the summary is based on the derived source pub.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_diff = self.addSummaryToDifference(ds_diff)

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertIsNot(None, view.summary)
        self.assertEqual(
            ds_diff.source_pub.meta_sourcepackage.summary, view.summary)

    def test_summary_for_missing_difference(self):
        # For packages only in the parent series, the summary is based
        # on the parent publication.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=(
                DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))
        ds_diff = self.addSummaryToDifference(ds_diff)

        view = create_initialized_view(ds_diff, '+listing-distroseries-extra')

        self.assertIsNot(None, view.summary)
        self.assertEqual(
            ds_diff.parent_source_pub.meta_sourcepackage.summary,
            view.summary)

    def test_summary_no_pubs(self):
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
        self.assertIs(None, view.summary)
