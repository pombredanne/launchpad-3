# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for person bug views."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.errors import UnexpectedFormData
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestBugSubscriberPackageBugsSearchListingView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriberPackageBugsSearchListingView, self).setUp()
        self.person = self.factory.makePerson()
        self.distribution = self.factory.makeDistribution()
        self.spn = self.factory.makeSourcePackageName()
        self.dsp = self.distribution.getSourcePackage(self.spn)

    def makeForm(self, package_name, distribution_name):
        return {
            'field.sourcepackagename': package_name,
            'field.distribution': distribution_name,
            'search': 'Search',
            }

    def test_current_package_known(self):
        # current_package contains the distribution source package that
        # matches the source package name.
        form = self.makeForm(self.spn.name, self.distribution.name)
        view = create_initialized_view(
            self.person, name='+packagebugs-search', form=form)
        self.assertEqual(self.dsp, view.current_package)

    def test_current_package_missing_distribution(self):
        # UnexpectedFormData is raised if the distribution is not provided.
        form = self.makeForm(self.spn.name, '')
        view = create_initialized_view(
            self.person, name='+packagebugs-search', form=form)
        self.assertRaises(
            UnexpectedFormData, getattr, view, 'current_package')

    def test_current_package_unknown_distribution(self):
        # UnexpectedFormData is raised if the distribution is not known.
        form = self.makeForm(self.spn.name, 'unknown-distribution')
        view = create_initialized_view(
            self.person, name='+packagebugs-search', form=form)
        self.assertRaises(
            UnexpectedFormData, getattr, view, 'current_package')

    def test_current_package_missing_sourcepackagename(self):
        # UnexpectedFormData is raised if the package name is not provided.
        form = self.makeForm('', self.distribution.name)
        view = create_initialized_view(
            self.person, name='+packagebugs-search', form=form)
        self.assertRaises(
            UnexpectedFormData, getattr, view, 'current_package')

    def test_current_package_unknown_sourcepackagename(self):
        # UnexpectedFormData is raised if the package name is not known.
        form = self.makeForm('unknown-package', self.distribution.name)
        view = create_initialized_view(
            self.person, name='+packagebugs-search', form=form)
        self.assertRaises(
            UnexpectedFormData, getattr, view, 'current_package')
