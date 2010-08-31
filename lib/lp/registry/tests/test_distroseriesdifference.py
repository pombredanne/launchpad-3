# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifference class."""

from __future__ import with_statement

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
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

    def test_source_version(self):
        # The version of the source in the derived series is returned.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew")

        self.assertEqual(
            ds_diff.source_pub.source_package_version, ds_diff.source_version)

    def test_source_version_none(self):
        # None is returned for source_version when there is no source pub.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            difference_type=(
                DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES))

        self.assertEqual(None, ds_diff.source_version)

    def test_updateStatusAndType_resolves_difference(self):
        # Status is set to resolved when versions match.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            versions={
                'parent': '1.0',
                'derived': '0.9',
                })
        new_derived_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series,
            status=PackagePublishingStatus.PENDING,
            version='1.0')

        was_updated = ds_diff.updateStatusAndType()

        self.assertTrue(was_updated)
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED,
            ds_diff.status)

    def test_updateStatusAndType_re_opens_difference(self):
        # The status of a resolved difference will updated with new
        # uploads.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            versions={
                'parent': '1.0',
                'derived': '1.0',
                },
            status=DistroSeriesDifferenceStatus.RESOLVED)
        new_derived_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series,
            status=PackagePublishingStatus.PENDING,
            version='1.1')

        was_updated = ds_diff.updateStatusAndType()

        self.assertTrue(was_updated)
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            ds_diff.status)

    def test_updateStatusAndType_new_version_no_change(self):
        # Uploading a new (different) version does not necessarily
        # update the record.
        # In this case, a new version is uploaded, but there is still a
        # difference needing attention.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            versions={
                'parent': '1.0',
                'derived': '0.9',
                })
        new_derived_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series,
            status=PackagePublishingStatus.PENDING,
            version='1.1')

        was_updated = ds_diff.updateStatusAndType()

        self.assertFalse(was_updated)
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            ds_diff.status)

    def test_updateStatusAndType_changes_type(self):
        # The type of difference is updated when appropriate.
        # In this case, a package that was previously only in the
        # derived series (UNIQUE_TO_DERIVED_SERIES), is uploaded
        # to the parent series with a different version.
        ds_diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foonew",
            versions={
                'derived': '0.9',
                },
            difference_type=(
                DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES))
        new_parent_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=ds_diff.source_package_name,
            distroseries=ds_diff.derived_series.parent_series,
            status=PackagePublishingStatus.PENDING,
            version='1.1')

        was_updated = ds_diff.updateStatusAndType()

        self.assertTrue(was_updated)
        self.assertEqual(
            DistroSeriesDifferenceType.DIFFERENT_VERSIONS,
            ds_diff.difference_type)

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

        with person_logged_in(ds_diff.owner):
            dsd_comment = ds_diff.addComment(
                ds_diff.owner, "Wait until version 2.1")

        self.assertEqual(ds_diff, dsd_comment.distro_series_difference)

    def test_getComments(self):
        # All comments for this difference are returned.
        ds_diff = self.factory.makeDistroSeriesDifference()

        with person_logged_in(ds_diff.owner):
            dsd_comment = ds_diff.addComment(
                ds_diff.owner, "Wait until version 2.1")
            dsd_comment_2 = ds_diff.addComment(
                ds_diff.owner, "Wait until version 2.1")

        self.assertEqual(
            [dsd_comment, dsd_comment_2], list(ds_diff.getComments()))

    def test_addComment_not_public(self):
        # Comments cannot be added with launchpad.View.
        ds_diff = self.factory.makeDistroSeriesDifference()
        person = self.factory.makePerson()

        with person_logged_in(person):
            self.assertTrue(check_permission('launchpad.View', ds_diff))
            self.assertFalse(check_permission('launchpad.Edit', ds_diff))
            self.assertRaises(Unauthorized, getattr, ds_diff, 'addComment')

    def test_addComment_for_owners(self):
        # Comments can be added by any of the owners of the derived
        # series.
        ds_diff = self.factory.makeDistroSeriesDifference()

        with person_logged_in(ds_diff.owner):
            self.assertTrue(check_permission('launchpad.Edit', ds_diff))
            diff_comment = ds_diff.addComment(
                ds_diff.derived_series.owner, "Boo")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
