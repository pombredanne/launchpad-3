# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Packaging content class."""

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility
from lazr.lifecycle.event import ObjectCreatedEvent

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.packaging import (
    IPackagingUtil,
    PackagingType,
    )
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.model.packaging import (
    Packaging,
    )
from lp.testing import (
    EventRecorder,
    login,
    TestCaseWithFactory,
    )


class TestPackaging(TestCaseWithFactory):
    """Test Packaging object."""

    layer = DatabaseFunctionalLayer

    def test_init_notifies(self):
        """Creating a Packaging should generate an event."""
        with EventRecorder() as recorder:
            packaging = Packaging()
        (event,) = recorder.events
        self.assertIsInstance(event, ObjectCreatedEvent)
        self.assertIs(packaging, event.object)


class PackagingUtilMixin:
    """Common items for testing IPackagingUtil."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.packaging_util = getUtility(IPackagingUtil)
        self.sourcepackagename = self.factory.makeSourcePackageName('sparkle')
        self.distroseries = self.factory.makeDistroRelease(name='dazzle')
        self.productseries = self.factory.makeProductSeries(name='glitter')
        self.owner = self.productseries.product.owner


class TestCreatePackaging(PackagingUtilMixin, TestCaseWithFactory):
    """Test PackagingUtil.packagingEntryExists."""

    def test_CreatePackaging_unique(self):
        """Packaging is unique distroseries+sourcepackagename."""
        self.packaging_util.createPackaging(
            self.productseries, self.sourcepackagename, self.distroseries,
            PackagingType.PRIME, owner=self.owner)
        sourcepackage = self.distroseries.getSourcePackage('sparkle')
        packaging = sourcepackage.direct_packaging
        self.assertEqual(packaging.distroseries, self.distroseries)
        self.assertEqual(packaging.sourcepackagename, self.sourcepackagename)
        self.assertEqual(packaging.productseries, self.productseries)

    def test_CreatePackaging_assert_unique(self):
        """Assert unique distroseries+sourcepackagename."""
        self.packaging_util.createPackaging(
            self.productseries, self.sourcepackagename, self.distroseries,
            PackagingType.PRIME, owner=self.owner)
        self.assertRaises(
            AssertionError, self.packaging_util.createPackaging,
            self.productseries, self.sourcepackagename, self.distroseries,
            PackagingType.PRIME, self.owner)


class TestPackagingEntryExists(PackagingUtilMixin, TestCaseWithFactory):
    """Test PackagingUtil.packagingEntryExists."""

    def setUpPackaging(self):
        self.packaging_util.createPackaging(
            self.productseries, self.sourcepackagename, self.distroseries,
            PackagingType.PRIME, owner=self.owner)

    def test_packagingEntryExists_false(self):
        """Verify that non-existent entries are false."""
        self.assertFalse(
            self.packaging_util.packagingEntryExists(
                sourcepackagename=self.sourcepackagename,
                distroseries=self.distroseries))

    def test_packagingEntryExists_unique(self):
        """Packaging entries are unique to distroseries+sourcepackagename."""
        self.setUpPackaging()
        self.assertTrue(
            self.packaging_util.packagingEntryExists(
                sourcepackagename=self.sourcepackagename,
                distroseries=self.distroseries))
        other_distroseries = self.factory.makeDistroRelease(name='shimmer')
        self.assertFalse(
            self.packaging_util.packagingEntryExists(
                sourcepackagename=self.sourcepackagename,
                distroseries=other_distroseries))

    def test_packagingEntryExists_specific(self):
        """Packaging entries are also specifc to both kinds of series."""
        self.setUpPackaging()
        self.assertTrue(
            self.packaging_util.packagingEntryExists(
                sourcepackagename=self.sourcepackagename,
                distroseries=self.distroseries,
                productseries=self.productseries))
        other_productseries = self.factory.makeProductSeries(name='flash')
        self.assertFalse(
            self.packaging_util.packagingEntryExists(
                sourcepackagename=self.sourcepackagename,
                distroseries=self.distroseries,
                productseries=other_productseries))


class TestDeletePackaging(TestCaseWithFactory):
    """Test PackagingUtil.deletePackaging.

    The essential functionality: deleting a Packaging record, is already
    covered in doctests.
    """

    layer = DatabaseFunctionalLayer

    def test_deleteNonExistentPackaging(self):
        """Deleting a non-existent Packaging fails.

        PackagingUtil.deletePackaging raises an Assertion error with a
        useful message if the specified Packaging record does not exist.
        """
        # Any authenticated user can delete a packaging entry.
        login('no-priv@canonical.com')

        # Get a SourcePackageName from the sample data.
        source_package_name_set = getUtility(ISourcePackageNameSet)
        firefox_name = source_package_name_set.queryByName('mozilla-firefox')

        # Get a DistroSeries from the sample data.
        distribution_set = getUtility(IDistributionSet)
        ubuntu_hoary = distribution_set.getByName('ubuntu').getSeries('hoary')

        # Get a ProductSeries from the sample data.
        product_set = getUtility(IProductSet)
        firefox_trunk = product_set.getByName('firefox').getSeries('trunk')

        # There must not be a packaging entry associating mozilla-firefox
        # ubunt/hoary to firefox/trunk.
        packaging_util = getUtility(IPackagingUtil)
        self.assertFalse(
            packaging_util.packagingEntryExists(
                productseries=firefox_trunk,
                sourcepackagename=firefox_name,
                distroseries=ubuntu_hoary),
            "This packaging entry should not exist in sample data.")

        # If we try to delete this non-existent entry, we get an
        # AssertionError with a helpful message.
        try:
            packaging_util.deletePackaging(
                productseries=firefox_trunk,
                sourcepackagename=firefox_name,
                distroseries=ubuntu_hoary)
        except AssertionError, exception:
            self.assertEqual(
                str(exception),
                "Tried to delete non-existent Packaging: "
                "productseries=trunk/firefox, "
                "sourcepackagename=mozilla-firefox, "
                "distroseries=ubuntu/hoary")
        else:
            self.fail("AssertionError was not raised.")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
