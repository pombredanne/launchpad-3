# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test questiontarget views."""

__metaclass__ = type

import os

from BeautifulSoup import BeautifulSoup

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import person_logged_in, TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestSearchQuestionsView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def linkPackage(self, product, name):
        # A helper to setup a legitimate Packaging link between a product
        # and an Ubuntu source package.
        hoary = getUtility(ILaunchpadCelebrities).ubuntu['hoary']
        sourcepackagename = self.factory.makeSourcePackageName(name)
        sourcepackage = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        product.development_focus.setPackaging(
            hoary, sourcepackagename, product.owner)


class TestSearchQuestionsViewTemplate(TestSearchQuestionsView):
    """Test the behaviour of SearchQuestionsView."""

    def assertViewTemplate(self, context, file_name):
        view = create_initialized_view(context, '+questions')
        self.assertEqual(
            file_name, os.path.basename(view.selected_template.filename))

    def test_template_product_official_answers_unknown(self):
        product = self.factory.makeProduct()
        self.assertViewTemplate(product, 'unknown-support.pt')

    def test_template_product_official_answers_launchpad(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner) as owner:
            product.official_answers = True
        self.assertViewTemplate(product, 'question-listing.pt')

    def test_template_projectgroup_official_answers_unknown(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner) as owner:
            product.project = project_group
        self.assertViewTemplate(project_group, 'unknown-support.pt')

    def test_template_projectgroup_official_answers_launchpad(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner) as owner:
            product.project = project_group
            product.official_answers = True
        self.assertViewTemplate(project_group, 'question-listing.pt')

    def test_template_distribution_official_answers_unknown(self):
        distribution = self.factory.makeDistribution()
        self.assertViewTemplate(distribution, 'unknown-support.pt')

    def test_template_distribution_official_answers_launchpad(self):
        distribution = self.factory.makeDistribution()
        with person_logged_in(distribution.owner) as owner:
            distribution.official_answers = True
        self.assertViewTemplate(distribution, 'question-listing.pt')

    def test_template_DSP_official_answers_unknown(self):
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertViewTemplate(dsp, 'unknown-support.pt')

    def test_template_DSP_official_answers_launchpad(self):
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(dsp.distribution.owner) as owner:
            dsp.distribution.official_answers = True
        self.assertViewTemplate(dsp, 'question-listing.pt')


class TestSearchQuestionsView_ubuntu_packages(TestSearchQuestionsView):
    """Test the behaviour of SearchQuestionsView.ubuntu_packages."""

    def test_nonproduct_ubuntu_packages(self):
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+questions')
        packages = view.ubuntu_packages
        self.assertEqual(None, packages)

    def test_product_ubuntu_packages_unlinked(self):
        product = self.factory.makeProduct()
        view = create_initialized_view(product, '+questions')
        packages = view.ubuntu_packages
        self.assertEqual(None, packages)

    def test_product_ubuntu_packages_linked(self):
        product = self.factory.makeProduct()
        self.linkPackage(product, 'cow')
        view = create_initialized_view(product, '+questions')
        packages = view.ubuntu_packages
        self.assertEqual(1, len(packages))
        self.assertEqual('cow', packages[0].name)


class TestSearchQuestionsViewUnknown(TestSearchQuestionsView):
    """Test the behaviour of SearchQuestionsView unknown support."""

    def setUp(self):
        super(TestSearchQuestionsViewUnknown, self).setUp()
        self.product = self.factory.makeProduct()
        self.view = create_initialized_view(self.product, '+questions')

    def test_common_page_elements(self):
        content = BeautifulSoup(self.view())
        robots = content.find('meta', attrs={'name': 'robots'})
        self.assertEqual('noindex,nofollow', robots['content'])
        self.assertTrue(content.find(True, id='support-unknown') is not None)

    def test_product_with_packaging_elements(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        hoary = ubuntu.getSeries('hoary')
        sourcepackagename = self.factory.makeSourcePackageName('cow')
        sourcepackage = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        self.product.development_focus.setPackaging(
            hoary, sourcepackagename, self.product.owner)
        content = BeautifulSoup(self.view())
        self.assertTrue(content.find(True, id='ubuntu-support') is not None)
