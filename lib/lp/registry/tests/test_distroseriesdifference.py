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
        self.assertRaises(
            NotADerivedSeriesError,
            self.factory.makeDistroSeriesDifference,
            derived_series=distro_series)

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
        src_name = self.factory.getOrMakeSourcePackageName("foonew")
        pending_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=src_name, distroseries=ds_diff.derived_series,
            status=PackagePublishingStatus.PENDING)

        self.assertEqual(pending_pub, ds_diff.source_pub)

    def test_parent_source_pub(self):
        # The related source pub for the parent distro series is returned.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        self.assertEqual(
            'foonew', ds_diff.parent_source_pub.source_package_name)
        self.assertEqual(
            ds_diff.derived_series.parent_series,
            ds_diff.parent_source_pub.distroseries)

    def test_paren_source_pub_gets_latest_pending(self):
        # The most recent publication is always returned, even if its pending.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")
        src_name = self.factory.getOrMakeSourcePackageName("foonew")
        pending_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=src_name,
            distroseries=ds_diff.derived_series.parent_series,
            status=PackagePublishingStatus.PENDING)

        self.assertEqual(pending_pub, ds_diff.parent_source_pub)

    def test_appendActivityLog(self):
        # The message is prepended with date/version info and appended
        # to the activity log with a new line.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        ds_diff.appendActivityLog("Waiting for version 1.9")

        self.assertIn(
            "Waiting for version 1.9\n",
            ds_diff.activity_log)

    def test_appendActivityLog_includes_username(self):
        # The username is included if a user is passed.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        ds_diff.appendActivityLog(
            "Waiting for version 1.9", ds_diff.derived_series.owner)

        self.assertIn(
            ds_diff.derived_series.owner.name,
            ds_diff.activity_log)

    def test_appendActivityLog_called_on_creation(self):
        # The creation of a difference is logged with initial versions.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            versions={
                'parent_series':'1.0',
                'derived_series': '0.9',
                })

        self.assertIn(
            'Initial parent/derived versions: 1.0/0.9',
            ds_diff.activity_log)

    def test_checkDifferenceType(self):
        self.fail("Unimplemented")

    def test_appendActivityLog_not_public(self):
        self.fail("Unimplemented")

    def test_pubs_are_cached(self):
        self.fail("Unimplemented")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
