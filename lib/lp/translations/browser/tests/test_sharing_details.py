# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,  
    LaunchpadFunctionalLayer,
    )
from lp.app.enums import ServiceUsage
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.translations.browser.sourcepackage import (
    SourcePackageTranslationSharingDetailsView,
    )
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )


class ConfigureUpstreamProjectMixin:
    """Provide a method for project configuration."""
    
    def configureUpstreamProject(self, productseries,
            set_upstream_branch=False, enable_translations=False,
            translation_import_mode=TranslationsBranchImportMode.NO_IMPORT):
        """Configure the productseries and its product as an upstream project."""
        with person_logged_in(productseries.product.owner):
            if set_upstream_branch:
                productseries.branch = self.factory.makeBranch(
                    product=productseries.product)
            if enable_translations:
                productseries.product.translations_usage = (
                    ServiceUsage.LAUNCHPAD)
            productseries.translations_autoimport_mode = (
                translation_import_mode)


class TestSourcePackageTranslationSharingDetailsView(TestCaseWithFactory,
                                            ConfigureUpstreamProjectMixin):
    """Tests for SourcePackageTranslationSharingStatus."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSourcePackageTranslationSharingDetailsView, self).setUp()
        distroseries = self.factory.makeUbuntuDistroSeries()
        self.sourcepackage = self.factory.makeSourcePackage(
            distroseries=distroseries)
        self.ubuntu_only_template = self.factory.makePOTemplate(
            sourcepackage=self.sourcepackage, name='ubuntu-only')
        self.shared_template_ubuntu_side = self.factory.makePOTemplate(
            sourcepackage=self.sourcepackage, name='shared-template')
        self.productseries = self.factory.makeProductSeries()
        self.shared_template_upstream_side = self.factory.makePOTemplate(
            productseries=self.productseries, name='shared-template')
        self.upstream_only_template = self.factory.makePOTemplate(
            productseries=self.productseries, name='upstream-only')
        self.view = SourcePackageTranslationSharingDetailsView(
            self.sourcepackage, LaunchpadTestRequest())
        self.view.initialize()

    def configureSharing(self,
            set_upstream_branch=False, enable_translations=False,
            translation_import_mode=TranslationsBranchImportMode.NO_IMPORT):
        """Configure translation sharing, at least partially.

        A packaging link is always set; the remaining configuration is
        done only if explicitly specified.
        """
        self.sourcepackage.setPackaging(
            self.productseries, self.productseries.owner)
        self.configureUpstreamProject(
            self.productseries, set_upstream_branch, enable_translations,
            translation_import_mode)

    def test_is_packaging_configured__not_configured(self):
        # If a sourcepackage is not linked to a product series,
        # SourcePackageTranslationSharingStatus.is_packaging_configured
        # returns False.
        self.assertFalse(self.view.is_packaging_configured)

    def test_is_packaging_configured__configured(self):
        # If a sourcepackage is linked to a product series,
        # SourcePackageTranslationSharingStatus.is_packaging_configured
        # returns True.
        self.configureSharing()
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
        self.configureSharing()
        self.assertFalse(self.view.has_upstream_branch)

    def test_has_upstream_branch__branch_exists(self):
        # If the upstream product series has at least one  source
        # code branch,
        # SourcePackageTranslationSharingStatus.has_upstream_branch
        # returns True.
        self.configureSharing(set_upstream_branch=True)
        self.assertTrue(self.view.has_upstream_branch)

    def test_is_upstream_translations_enabled__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_translations_enabled returns False.
        self.assertFalse(self.view.is_upstream_translations_enabled)

    def test_is_upstream_translations_enabled__when_disabled(self):
        # If the upstream product series does not use Launchpad for
        # translations, is_upstream_translations_enabled returns False.
        self.configureSharing()
        self.assertFalse(self.view.is_upstream_translations_enabled)

    def test_is_upstream_translations_enabled__when_enabled(self):
        # If the upstream product series uses Launchpad for
        # translations, is_upstream_translations_enabled returns True.
        self.configureSharing(enable_translations=True)
        self.assertTrue(self.view.is_upstream_translations_enabled)

    def test_is_upstream_synchronization_enabled__no_packaging_link(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__no_import(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.configureSharing(
            translation_import_mode=TranslationsBranchImportMode.NO_IMPORT)
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__import_templates(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.configureSharing(
            translation_import_mode=
                TranslationsBranchImportMode.IMPORT_TEMPLATES)
        self.assertFalse(self.view.is_upstream_synchronization_enabled)

    def test_is_upstream_synchronization_enabled__import_translations(self):
        # If the source package is not linked to an upstream series,
        # is_upstream_synchronization_enabled returns False.
        self.configureSharing(
            translation_import_mode=
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
        self.configureSharing()
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__packaging_upstream_branch_set(self):
        # If the packaging link is set and if an upstream branch is
        # configuerd but if the other conditions are not fulfilled,
        # is_configuration_complete is False.
        self.configureSharing(set_upstream_branch=True)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__packaging_transl_enabled(self):
        # If the packaging link is set and if an upstream series
        # uses Launchpad translations but if the other conditions
        # are not fulfilled, is_configuration_complete is False.
        self.configureSharing(enable_translations=True)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__no_auto_sync(self):
        # If
        #   - a packaging link is set
        #   - a branch is set for the upstream series
        #   - the upstream series uses Launchpad translations
        # but if the upstream series does not synchronize translations
        # then is_configuration_complete is False.
        self.configureSharing(
            set_upstream_branch=True, enable_translations=True)
        self.assertFalse(self.view.is_configuration_complete)

    def test_is_configuration_complete__all_conditions_fulfilled(self):
        # If
        #   - a packaging link is set
        #   - a branch is set for the upstream series
        #   - the upstream series uses Launchpad translations
        #   - the upstream series synchronizes translations
        # then is_configuration_complete is True.
        self.configureSharing(
            set_upstream_branch=True, enable_translations=True,
            translation_import_mode=
                TranslationsBranchImportMode.IMPORT_TRANSLATIONS)
        self.assertTrue(self.view.is_configuration_complete)

    def test_template_info__no_sharing(self):
        # If translation sharing is not configured,
        # SourcePackageTranslationSharingDetailsView.info returns
        # only data about templates in Ubuntu.
        expected = [
            {
                'name': 'shared-template',
                'status': 'only in Ubuntu',
                'package_template': self.shared_template_ubuntu_side,
                'upstream_template': None,
                },
            {
                'name': 'ubuntu-only',
                'status': 'only in Ubuntu',
                'package_template': self.ubuntu_only_template,
                'upstream_template': None,
                },
            ]
        self.assertEqual(expected, self.view.template_info)

    def test_template_info___sharing(self):
        # If translation sharing is configured,
        # SourcePackageTranslationSharingDetailsView.info returns
        # only data about templates in Ubuntu and about upstream
        # templates.
        self.configureSharing(
            set_upstream_branch=True, enable_translations=True,
            translation_import_mode=
                TranslationsBranchImportMode.IMPORT_TRANSLATIONS)
        expected = [
            {
                'name': 'shared-template',
                'status': 'shared',
                'package_template': self.shared_template_ubuntu_side,
                'upstream_template': self.shared_template_upstream_side,
                },
            {
                'name': 'ubuntu-only',
                'status': 'only in Ubuntu',
                'package_template': self.ubuntu_only_template,
                'upstream_template': None,
                },
            {
                'name': 'upstream-only',
                'status': 'only in upstream',
                'package_template': None,
                'upstream_template': self.upstream_only_template,
                },
            ]
        self.assertEqual(expected, self.view.template_info)


class TestSourcePackageSharingDetailsPage(BrowserTestCase,
                                          ConfigureUpstreamProjectMixin):
    """Test for the sharing details page of a source package."""

    layer = DatabaseFunctionalLayer

    def _makeSourcePackage(self):
        """Make a source package in Ubuntu."""
        distroseries = self.factory.makeUbuntuDistroSeries()
        return self.factory.makeSourcePackage(distroseries=distroseries)

    def test_checklist_unconfigured(self):
        # Without a packaging link, sharing is completely unconfigured
        sourcepackage = self._makeSourcePackage()
        browser = self.getViewBrowser(
            sourcepackage, no_login=True, rootsite="translations",
            view_name="+sharing-details")
        checklist = find_tag_by_id(browser.contents, 'sharing-checklist')
        self.assertIsNot(None, checklist)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Translation sharing configuration is incomplete.
            No upstream project series has been linked. Change upstream link
            No source branch exists for the upstream series.
            Translations are not enabled on the upstream series.
            Automatic synchronization of translations is not enabled.""",
            extract_text(checklist))

    def test_checklist_partly_configured(self):
        # Linking a source package takes care of one item.
        packaging = self.factory.makePackagingLink(in_ubuntu=True)
        browser = self.getViewBrowser(
            packaging.sourcepackage, no_login=True, rootsite="translations",
            view_name="+sharing-details")
        checklist = find_tag_by_id(browser.contents, 'sharing-checklist')
        self.assertIsNot(None, checklist)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Translation sharing configuration is incomplete.
            Linked upstream series is .+ trunk series.
                Change upstream link Remove upstream link
            No source branch exists for the upstream series.
            Translations are not enabled on the upstream series.
            Automatic synchronization of translations is not enabled.""",
            extract_text(checklist))

    def test_checklist_fully_configured(self):
        # A fully configured sharing setup.
        packaging = self.factory.makePackagingLink(in_ubuntu=True)
        productseries = packaging.productseries
        self.configureUpstreamProject(
            productseries,
            set_upstream_branch=True, enable_translations=True,
            translation_import_mode=(
                TranslationsBranchImportMode.IMPORT_TRANSLATIONS))
        browser = self.getViewBrowser(
            packaging.sourcepackage, no_login=True, rootsite="translations",
            view_name="+sharing-details")
        checklist = find_tag_by_id(browser.contents, 'sharing-checklist')
        self.assertIsNot(None, checklist)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Translation sharing with upstream is active.
            Linked upstream series is .+ trunk series.
                Change upstream link Remove upstream link
            Upstream source branch is .+[.]
            Translations are enable on the upstream project.
            Automatic synchronization of translations is enabled.""",
            extract_text(checklist))
