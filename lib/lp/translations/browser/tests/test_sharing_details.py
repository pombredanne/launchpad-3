# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.enums import ServiceUsage
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.translations.browser.sourcepackage import (
    SourcePackageTranslationSharingDetailsView,
    )
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )


class TestSourcePackageTranslationSharingDetailsView(TestCaseWithFactory):
    """Tests for SourcePackageTranslationSharingStatus."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSourcePackageTranslationSharingDetailsView, self).setUp()
        self.sourcepackage = self.factory.makeSourcePackage()
        self.productseries = self.factory.makeProductSeries()
        self.view = SourcePackageTranslationSharingDetailsView(
            self.sourcepackage, LaunchpadTestRequest())
        self.view.initialize()

    def test_is_packaging_configured__not_configured(self):
        # If a sourcepackage is not linked to a product series,
        # SourcePackageTranslationSharingStatus.is_packaging_configured
        # returns False.
        self.assertFalse(self.view.is_packaging_configured)

    def test_is_packaging_configured__configured(self):
        # If a sourcepackage is linked to a product series,
        # SourcePackageTranslationSharingStatus.is_packaging_configured
        # returns True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertTrue(self.view.is_packaging_configured)

    def test_has_upstream_branch__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # SourcePackageTranslationSharingStatus.has_upstream_branch
        # returns False.
        self.assertFalse(self.view.has_upstream_branch)

    def test_has_upstream_branch__no_branch_exists(self):
        # If the upstream product series does not have any source
        # code branch,
        # SourcePackageTranslationSharingStatus.has_upstream_branch
        # returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertFalse(self.view.has_upstream_branch)

    def test_has_upstream_branch__branch_exists(self):
        # If the upstream product series has at least one  source
        # code branch,
        # SourcePackageTranslationSharingStatus.has_upstream_branch
        # returns True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            self.productseries.branch = self.factory.makeBranch(
                product=self.productseries.product)
        self.assertTrue(self.view.has_upstream_branch)

    def test_is_upstream_translations_enabled__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_translations_enabled returns False.
        self.assertFalse(self.view.is_upstream_translations_enabled)

    def test_is_upstream_translations_enabled__when_disabled(self):
        # If the upstream product series does not use Launchpad for
        # translations, is_upstream_translations_enabled returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertFalse(self.view.is_upstream_translations_enabled)

    def test_is_upstream_translations_enabled__when_enabled(self):
        # If the upstream product series uses Launchpad for
        # translations, is_upstream_translations_enabled returns True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.translations_usage = (
                ServiceUsage.LAUNCHPAD)
        self.assertTrue(self.view.is_upstream_translations_enabled)

    def test_is_upstream_synchronization_enabled__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__no_import(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            self.productseries.translations_autoimport_mode = (
                TranslationsBranchImportMode.NO_IMPORT)
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__import_templates(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            self.productseries.translations_autoimport_mode = (
                TranslationsBranchImportMode.IMPORT_TEMPLATES)
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__import_translations(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            self.productseries.translations_autoimport_mode = (
                TranslationsBranchImportMode.IMPORT_TRANSLATIONS)
        self.assertTrue(self.view.is_upstream_synchronization_enabled)

    def test_is_configuration_complete__nothing_configured(self):
        # If none of the conditions for translation sharing are
        # fulfilled (the default test setup), is_configuration_complete
        # is False.
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__only_packaging_set(self):
        # If the packaging link is set but the other conditions for
        # translation sharing are not fulfilled, is_configuration_complete
        # is False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__packaging_upstream_branch_set(self):
        # If the packaging link is set and if an upstream branch is
        # configuerd but if the other conditions are not fulfilled,
        # is_configuration_complete is False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.owner):
            branch = self.factory.makeBranch(
                product=self.productseries.product)
            self.productseries.branch = branch
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__packaging_transl_enabled(self):
        # If the packaging link is set and if an upstream series
        # uses Launchpad translations but if the other conditions
        # are not fulfilled, is_configuration_complete is False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.translations_usage = (
                ServiceUsage.LAUNCHPAD)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__no_auto_sync(self):
        # If
        #   - a packaging link is set
        #   - a branch is set for the upstream series
        #   - the upstream series uses Launchpad translations
        # but if the upstream series does not synchronize translations
        # then is_configuration_complete is False.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.translations_usage = (
                ServiceUsage.LAUNCHPAD)
            self.productseries.branch = self.factory.makeBranch(
                product=self.productseries.product)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__all_conditions_fulfilled(self):
        # If
        #   - a packaging link is set
        #   - a branch is set for the upstream series
        #   - the upstream series uses Launchpad translations
        #   - the upstream series synchronizes translations
        # then is_configuration_complete is True.
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.translations_usage = (
                ServiceUsage.LAUNCHPAD)
            self.productseries.branch = self.factory.makeBranch(
                product=self.productseries.product)
            self.productseries.translations_autoimport_mode = (
                TranslationsBranchImportMode.IMPORT_TRANSLATIONS)
        self.assertTrue(self.view.is_configuration_complete)
