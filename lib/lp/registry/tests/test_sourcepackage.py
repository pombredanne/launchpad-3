# Copyright 2009, 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for ISourcePackage implementations."""

__metaclass__ = type

import unittest

from storm.locals import Store
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    login_person,
    logout,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.seriessourcepackagebranch import (
    IMakeOfficialBranchLinks,
    )
from lp.registry.interfaces.distribution import NoPartnerArchive
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.packaging import Packaging
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.views import create_initialized_view


class TestSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        person = self.factory.makePerson()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        removeSecurityProxy(ubuntu_branches).addMember(
            person, ubuntu_branches.teamowner)
        login_person(person)
        self.addCleanup(logout)

    def test_path(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual(
            '%s/%s/%s' % (
                sourcepackage.distribution.name,
                sourcepackage.distroseries.name,
                sourcepackage.sourcepackagename.name),
            sourcepackage.path)

    def test_getBranch_no_branch(self):
        # If there's no official branch for that pocket of a source package,
        # getBranch returns None.
        sourcepackage = self.factory.makeSourcePackage()
        branch = sourcepackage.getBranch(PackagePublishingPocket.RELEASE)
        self.assertIs(None, branch)

    def test_getBranch_exists(self):
        # If there is a SeriesSourcePackageBranch entry for that source
        # package and pocket, then return the branch.
        sourcepackage = self.factory.makeSourcePackage()
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        getUtility(IMakeOfficialBranchLinks).new(
            sourcepackage.distroseries, PackagePublishingPocket.RELEASE,
            sourcepackage.sourcepackagename, branch, registrant)
        official_branch = sourcepackage.getBranch(
            PackagePublishingPocket.RELEASE)
        self.assertEqual(branch, official_branch)

    def test_setBranch(self):
        # We can set the official branch for a pocket of a source package.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        self.assertEqual(branch, sourcepackage.getBranch(pocket))

    def test_change_branch_once_set(self):
        # We can change the official branch for a a pocket of a source package
        # even after it has already been set.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        new_branch = self.factory.makePackageBranch(
            sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        sourcepackage.setBranch(pocket, new_branch, registrant)
        self.assertEqual(new_branch, sourcepackage.getBranch(pocket))

    def test_unsetBranch(self):
        # Setting the official branch for a pocket to 'None' breaks the link
        # between the branch and pocket.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        sourcepackage.setBranch(pocket, None, registrant)
        self.assertIs(None, sourcepackage.getBranch(pocket))

    def test_linked_branches(self):
        # ISourcePackage.linked_branches is a mapping of pockets to branches.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        self.assertEqual(
            [(pocket, branch)], list(sourcepackage.linked_branches))

    def test_getSuiteSourcePackage(self):
        # ISourcePackage.getSuiteSourcePackage returns the suite source
        # package object for the given pocket.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        ssp = sourcepackage.getSuiteSourcePackage(pocket)
        self.assertEqual(sourcepackage, ssp.sourcepackage)
        self.assertEqual(pocket, ssp.pocket)

    def test_path_to_release_pocket(self):
        # ISourcePackage.getPocketPath returns the path to a pocket. For the
        # RELEASE pocket, it's the same as the package path.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        self.assertEqual(
            sourcepackage.path, sourcepackage.getPocketPath(pocket))

    def test_path_to_non_release_pocket(self):
        # ISourcePackage.getPocketPath returns the path to a pocket. For a
        # non-RELEASE pocket, it's the same as the package path, except with
        # series-pocket for the middle component.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.SECURITY
        path = '%s/%s-%s/%s' % (
            sourcepackage.distribution.name,
            sourcepackage.distroseries.name,
            pocket.name.lower(),
            sourcepackage.name)
        self.assertEqual(path, sourcepackage.getPocketPath(pocket))

    def test_development_version(self):
        # ISourcePackage.development_version gets the development version of
        # the source package.
        distribution = self.factory.makeDistribution()
        dev_series = self.factory.makeDistroRelease(
            distribution=distribution, status=SeriesStatus.DEVELOPMENT)
        other_series = self.factory.makeDistroRelease(
            distribution=distribution, status=SeriesStatus.OBSOLETE)
        self.assertEqual(dev_series, distribution.currentseries)
        dev_sourcepackage = self.factory.makeSourcePackage(
            distroseries=dev_series)
        other_sourcepackage = self.factory.makeSourcePackage(
            distroseries=other_series,
            sourcepackagename=dev_sourcepackage.sourcepackagename)
        self.assertEqual(
            dev_sourcepackage, other_sourcepackage.development_version)
        self.assertEqual(
            dev_sourcepackage, dev_sourcepackage.development_version)

    def test_distribution_sourcepackage(self):
        # ISourcePackage.distribution_sourcepackage is the distribution source
        # package for the ISourcePackage.
        sourcepackage = self.factory.makeSourcePackage()
        distribution = sourcepackage.distribution
        distribution_sourcepackage = distribution.getSourcePackage(
            sourcepackage.sourcepackagename)
        self.assertEqual(
            distribution_sourcepackage,
            sourcepackage.distribution_sourcepackage)

    def test_default_archive(self):
        # The default archive of a source package is the primary archive of
        # its distribution.
        sourcepackage = self.factory.makeSourcePackage()
        distribution = sourcepackage.distribution
        self.assertEqual(
            distribution.main_archive, sourcepackage.get_default_archive())

    def test_default_archive_partner(self):
        # If the source package was most recently uploaded to a partner
        # component, then its default archive is the partner archive for the
        # distribution.
        sourcepackage = self.factory.makeSourcePackage()
        partner = getUtility(IComponentSet)['partner']
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackage.sourcepackagename,
            distroseries=sourcepackage.distroseries,
            component=partner,
            status=PackagePublishingStatus.PUBLISHED)
        distribution = sourcepackage.distribution
        expected_archive = self.factory.makeArchive(
            distribution=distribution,
            purpose=ArchivePurpose.PARTNER)
        self.assertEqual(
            expected_archive, sourcepackage.get_default_archive())

    def test_default_archive_specified_component(self):
        # If the component is explicitly specified as partner, then we return
        # the partner archive.
        sourcepackage = self.factory.makeSourcePackage()
        partner = getUtility(IComponentSet)['partner']
        distribution = sourcepackage.distribution
        expected_archive = self.factory.makeArchive(
            distribution=distribution,
            purpose=ArchivePurpose.PARTNER)
        self.assertEqual(
            expected_archive,
            sourcepackage.get_default_archive(component=partner))

    def test_default_archive_partner_doesnt_exist(self):
        # If the default archive ought to be the partner archive (because the
        # last published upload was to a partner component) then
        # default_archive will raise an exception.
        sourcepackage = self.factory.makeSourcePackage()
        partner = getUtility(IComponentSet)['partner']
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackage.sourcepackagename,
            distroseries=sourcepackage.distroseries,
            component=partner,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertRaises(
            NoPartnerArchive, sourcepackage.get_default_archive)

    def test_source_package_summary_no_releases_returns_None(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual(sourcepackage.summary, None)

    def test_source_package_summary_with_releases_returns_None(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.factory.makeSourcePackageRelease(
            sourcepackagename=sourcepackage.sourcepackagename)
        self.assertEqual(sourcepackage.summary, None)

    def test_source_package_summary_with_binaries_returns_list(self):
        sp = getUtility(
            ILaunchpadCelebrities).ubuntu['warty'].getSourcePackage(
            'mozilla-firefox')

        expected_summary = (
            u'mozilla-firefox: Mozilla Firefox Web Browser\n'
            u'mozilla-firefox-data: No summary available for '
            u'mozilla-firefox-data in ubuntu warty.')
        self.assertEqual(''.join(expected_summary), sp.summary)

    def test_deletePackaging(self):
        """Ensure deletePackaging completely removes packaging."""
        packaging = self.factory.makePackagingLink()
        packaging_id = packaging.id
        store = Store.of(packaging)
        packaging.sourcepackage.deletePackaging()
        result = store.find(Packaging, Packaging.id==packaging_id)
        self.assertIs(None, result.one())


class TestSourcePackageWebService(WebServiceTestCase):

    def test_setPackaging(self):
        """setPackaging is accessible and works."""
        sourcepackage = self.factory.makeSourcePackage()
        self.assertIs(None, sourcepackage.direct_packaging)
        productseries = self.factory.makeProductSeries()
        transaction.commit()
        ws_sourcepackage = self.wsObject(sourcepackage)
        ws_productseries = self.wsObject(productseries)
        ws_sourcepackage.setPackaging(productseries=ws_productseries)
        transaction.commit()
        self.assertEqual(
            productseries, sourcepackage.direct_packaging.productseries)

    def test_deletePackaging(self):
        """Deleting a packaging should work."""
        packaging = self.factory.makePackagingLink()
        sourcepackage = packaging.sourcepackage
        transaction.commit()
        self.wsObject(sourcepackage).deletePackaging()
        transaction.commit()
        self.assertIs(None, sourcepackage.direct_packaging)

    def test_deletePackaging_with_no_packaging(self):
        """Deleting when there's no packaging should be a no-op."""
        sourcepackage = self.factory.makeSourcePackage()
        transaction.commit()
        self.wsObject(sourcepackage).deletePackaging()
        transaction.commit()
        self.assertIs(None, sourcepackage.direct_packaging)


class TestSourcePackageSecurity(TestCaseWithFactory):
    """Tests for source package branch linking security."""

    layer = DatabaseFunctionalLayer

    def test_cannot_setBranch(self):
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        self.assertRaises(
            Unauthorized, sourcepackage.setBranch, pocket, branch, registrant)


class TestSourcePackageViews(TestCaseWithFactory):
    """Tests for source package view classes."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.owner = self.factory.makePerson()
        self.product = self.factory.makeProduct(
            name='bonkers', displayname='Bonkers', owner=self.owner)

        self.obsolete_productseries = self.factory.makeProductSeries(
            name='obsolete', product=self.product)
        with person_logged_in(self.product.owner):
            self.obsolete_productseries.status = SeriesStatus.OBSOLETE

        self.dev_productseries = self.factory.makeProductSeries(
            name='current', product=self.product)
        with person_logged_in(self.product.owner):
            self.dev_productseries.status = SeriesStatus.DEVELOPMENT

        self.distribution = self.factory.makeDistribution(
            name='youbuntu', displayname='Youbuntu', owner=self.owner)
        self.distroseries = self.factory.makeDistroRelease(name='busy',
            distribution=self.distribution)
        self.sourcepackagename = self.factory.makeSourcePackageName(
            name='bonkers')
        self.package = self.factory.makeSourcePackage(
            sourcepackagename=self.sourcepackagename,
            distroseries=self.distroseries)

    def test_editpackaging_obsolete_series_in_vocabulary(self):
        # The sourcepackage's current product series is included in
        # the vocabulary even if it is obsolete.
        self.package.setPackaging(self.obsolete_productseries, self.owner)
        form = {
            'field.product': 'bonkers',
            'field.actions.continue': 'Continue',
            'field.__visited_steps__': 'sourcepackage_change_upstream_step1',
            }
        view = create_initialized_view(
            self.package, name='+edit-packaging', form=form,
            principal=self.owner)
        self.assertEqual([], view.view.errors)
        self.assertEqual(
            self.obsolete_productseries,
            view.view.form_fields['productseries'].field.default,
            "The form's default productseries must be the current one.")
        options = [term.token
                   for term in view.view.widgets['productseries'].vocabulary]
        self.assertEqual(
            ['trunk', 'current', 'obsolete'], options,
            "The obsolete series must be in the vocabulary.")

    def test_editpackaging_obsolete_series_not_in_vocabulary(self):
        # Obsolete productseries are normally not in the vocabulary.
        form = {
            'field.product': 'bonkers',
            'field.actions.continue': 'Continue',
            'field.__visited_steps__': 'sourcepackage_change_upstream_step1',
            }
        view = create_initialized_view(
            self.package, name='+edit-packaging', form=form,
            principal=self.owner)
        self.assertEqual([], view.view.errors)
        self.assertEqual(
            None,
            view.view.form_fields['productseries'].field.default,
            "The form's default productseries must be None.")
        options = [term.token
                   for term in view.view.widgets['productseries'].vocabulary]
        self.assertEqual(
            ['trunk', 'current'], options,
            "The obsolete series must NOT be in the vocabulary.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
