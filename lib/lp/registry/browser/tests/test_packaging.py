# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser tests for Packaging actions."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.packaging import IPackagingUtil
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.testing.pages import setupBrowser
from canonical.testing import PageTestLayer


class TestBrowserDeletePackaging(TestCase):
    """Browser tests for deletion of Packaging objects."""

    layer = PageTestLayer

    def setUp(self):
        self.user_browser = setupBrowser(
            auth="Basic no-priv@canonical.com:test")

    def test_deletionIsPersistent(self):
        # Test that deleting a Packaging entry is persistent.
        #
        # When developing the initial Packaging deletion feature, we hit a bug
        # where submitting the Packaging deletion form apparently worked, and
        # rendered a page where the deleted Packaging was not present, but a
        # silent error occurred while rendering the page, which caused the
        # transaction to abort. As a consequence, the Packaging deletion was
        # not recorded, and reloading the page would make the deleted
        # Packaging data reappear on the page.
        # Check sampledata expectations
        login('no-priv@canonical.com')
        source_package_name_set = getUtility(ISourcePackageNameSet)
        package_name = source_package_name_set.queryByName('alsa-utils')
        distribution_set = getUtility(IDistributionSet)
        distroseries = distribution_set.getByName('ubuntu').getSeries('warty')
        product_set = getUtility(IProductSet)
        product = product_set.getByName('alsa-utils')
        productseries = product.getSeries('trunk')
        packaging_util = getUtility(IPackagingUtil)
        self.assertTrue(packaging_util.packagingEntryExists(
            productseries=productseries,
            sourcepackagename=package_name,
            distroseries=distroseries))
        logout()
        # Delete the packaging
        user_browser = self.user_browser
        user_browser.open('http://launchpad.dev/ubuntu/+source/alsa-utils')
        form = user_browser.getForm("delete_warty_alsa-utils_trunk")
        form.getControl(name="field.actions.delete_packaging").click()
        # Check that the change was committed.
        login('no-priv@canonical.com')
        self.assertFalse(packaging_util.packagingEntryExists(
            productseries=productseries,
            sourcepackagename=package_name,
            distroseries=distroseries))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

