# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the Packaging content class."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSet, IProductSet, ISourcePackageNameSet, IPackagingUtil)
from canonical.launchpad.ftests import login
from canonical.testing import LaunchpadFunctionalLayer


class TestDeletePackaging(TestCase):
    """Test PackagingUtil.deletePackaging.

    The essential functionality: deleting a Packaging record, is already
    covered in doctests.
    """

    layer = LaunchpadFunctionalLayer

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

        # If we try to delete this non-existent entry, we get an AssertionError
        # with a helpful message.
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

