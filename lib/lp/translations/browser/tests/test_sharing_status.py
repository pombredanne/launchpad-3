# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.translations.browser.sourcepackage import (
    SourcePackageTranslationSharingStatus,
    )


class TestSourcePackageTranslationSharingStatus(TestCaseWithFactory):
    """Tests for SourcePackageTranslationSharingStatus."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSourcePackageTranslationSharingStatus, self).setUp()
        self.sourcepackage = self.factory.makeSourcePackage()
        self.productseries = self.factory.makeProductSeries()
        self.view = SourcePackageTranslationSharingStatus(
            self.sourcepackage, LaunchpadTestRequest())
        self.view.initialize()

    def test_packaging_configured__not_configured(self):
        # If a sourcepackage is not linked to a product series,
        # SourcePackageTranslationSharingStatus.packaging_configured
        # returns False.
        self.assertFalse(self.view.packaging_configured)

    def test_packaging_configured__configured(self):
        # If a sourcepackage is linked to a product series,
        # SourcePackageTranslationSharingStatus.packaging_configured
        # returns True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertTrue(self.view.packaging_configured)

    def test_has_upstream_branch__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # SourcePackageTranslationSharingStatus.upstream_branch_exists
        # returns False.
        self.assertFalse(self.view.has_upstream_branch)

    def test_has_upstream_branch__no_branch_exists(self):
        # If the upstream product series does not have any source
        # code branch,
        # SourcePackageTranslationSharingStatus.upstream_branch_exists
        # returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertFalse(self.view.has_upstream_branch)

    def test_has_upstream_branch__branch_exists(self):
        # If the upstream product series has at least one  source
        # code branch,
        # SourcePackageTranslationSharingStatus.upstream_branch_exists
        # returns True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            branch = self.factory.makeBranch(
                product=self.productseries.product)
            self.productseries.branch = branch
        self.assertTrue(self.view.has_upstream_branch)
