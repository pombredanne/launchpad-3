# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifference class."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.registry.enum import DistroSeriesDifferenceType
from lp.registry.exceptions import NotADerivedSeriesError
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    IDistroSeriesDifferenceSource,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        # The implementation implements the interface correctly.
        ds_diff = self.factory.makeDistroSeriesDifference()
        # Flush the store to ensure db constraints are triggered.
        Store.of(ds_diff).flush()

        verifyObject(IDistroSeriesDifference, ds_diff)

    def test_source_implements_interface(self):
        # The utility for creating differences implements its interface.
        utility = getUtility(IDistroSeriesDifferenceSource)

        verifyObject(IDistroSeriesDifferenceSource, utility)

    def test_new_non_derived_series(self):
        # A DistroSeriesDifference cannot be created with a non-derived
        # series.
        distro_series = self.factory.makeDistroSeries()
        source_package_name = self.factory.makeSourcePackageName('myfoo')
        distroseriesdifference_factory = getUtility(
            IDistroSeriesDifferenceSource)

        self.assertRaises(
            NotADerivedSeriesError, distroseriesdifference_factory.new,
            distro_series, source_package_name,
            DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES,
            )

    def test_source_pub(self):
        # The related source pub is returned for the derived series.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        self.assertEqual(
            'foonew', ds_diff.source_pub.source_package_name)
        self.assertEqual(
            ds_diff.derived_series, ds_diff.source_pub.distroseries)

    def test_source_pub_gets_latest_pending(self):
        # The most recent publication is always returned, even if its pending.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")
        pending_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series,
            status=PackagePublishingStatus.PENDING)

        self.assertEqual(pending_pub, ds_diff.source_pub)

    def test_source_pub_returns_none(self):
        # None is returned when there is no source pub.
        ds_diff = self.factory.makeDistroSeriesDifference(
            difference_type=(
                DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))

        self.assertIs(None, ds_diff.source_pub)

    def test_parent_source_pub(self):
        # The related source pub for the parent distro series is returned.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        self.assertEqual(
            'foonew', ds_diff.parent_source_pub.source_package_name)
        self.assertEqual(
            ds_diff.derived_series.parent_series,
            ds_diff.parent_source_pub.distroseries)

    def test_parent_source_pub_gets_latest_pending(self):
        # The most recent publication is always returned, even if its pending.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")
        pending_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series.parent_series,
            status=PackagePublishingStatus.PENDING)

        self.assertEqual(pending_pub, ds_diff.parent_source_pub)

    def test_title(self):
        # The title is a friendly description of the difference.
        parent_series = self.factory.makeDistroSeries(name="lucid")
        derived_series = self.factory.makeDistroSeries(
            parent_series=parent_series, name="derilucid")
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew", derived_series=derived_series,
            versions={
                'parent': '1.0',
                'derived': '0.9',
                })

        self.assertEqual(
            "Difference between distroseries 'Lucid' and 'Derilucid' "
            "for package 'foonew' (1.0/0.9)",
            ds_diff.title)

    def test_addComment(self):
        # Adding a comment creates a new DistroSeriesDifferenceComment
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")
        person = self.factory.makePerson()

        dsd_comment = ds_diff.addComment(person, "Wait until version 2.1")

        self.assertEqual(ds_diff, dsd_comment.distro_series_difference)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
