# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the product view classes and templates."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.publisher.interfaces import NotFound

from lp.code.browser.branchlisting import (
    DistributionBranchListingView,
    GroupedDistributionSourcePackageBranchesView,
    PersonProductBranchesView,
    ProductBranchesView,
    )
from lp.code.browser.gitlisting import (
    PersonTargetGitListingView,
    PlainGitListingView,
    TargetGitListingView,
    )
from lp.registry.enums import VCSType
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.publication import test_traverse


class TestProductDefaultVCSView(TestCaseWithFactory):
    """Tests that Product:+code delegates to +git or +branches."""

    layer = DatabaseFunctionalLayer

    def assertCodeViewClass(self, vcs, cls):
        product = self.factory.makeProduct(vcs=vcs)
        self.assertEqual(vcs, product.vcs)
        view = test_traverse('/%s/+code' % product.name)[1]
        self.assertIsInstance(view, cls)

    def test_default_unset(self):
        self.assertCodeViewClass(None, ProductBranchesView)

    def test_default_bzr(self):
        self.assertCodeViewClass(VCSType.BZR, ProductBranchesView)

    def test_git(self):
        self.assertCodeViewClass(VCSType.GIT, TargetGitListingView)


class TestPersonProductDefaultVCSView(TestCaseWithFactory):
    """Tests that PersonProduct:+code delegates to +git or +branches."""

    layer = DatabaseFunctionalLayer

    def assertCodeViewClass(self, vcs, cls):
        person = self.factory.makePerson()
        product = self.factory.makeProduct(vcs=vcs)
        self.assertEqual(vcs, product.vcs)
        view = test_traverse('/~%s/%s/+code' % (person.name, product.name))[1]
        self.assertIsInstance(view, cls)

    def test_default_unset(self):
        self.assertCodeViewClass(None, PersonProductBranchesView)

    def test_default_bzr(self):
        self.assertCodeViewClass(VCSType.BZR, PersonProductBranchesView)

    def test_git(self):
        self.assertCodeViewClass(VCSType.GIT, PersonTargetGitListingView)


class TestDistributionSourcePackageDefaultVCSView(TestCaseWithFactory):
    """Tests that DSP:+code delegates to +git or +branches."""

    layer = DatabaseFunctionalLayer

    def assertCodeViewClass(self, vcs, cls):
        distro = self.factory.makeDistribution(vcs=vcs)
        dsp = self.factory.makeDistributionSourcePackage(distribution=distro)
        self.assertEqual(vcs, distro.vcs)
        view = test_traverse(
            '/%s/+source/%s/+code'
            % (distro.name, dsp.sourcepackagename.name))[1]
        self.assertIsInstance(view, cls)

    def test_default_unset(self):
        self.assertCodeViewClass(
            None, GroupedDistributionSourcePackageBranchesView)

    def test_default_bzr(self):
        self.assertCodeViewClass(
            VCSType.BZR, GroupedDistributionSourcePackageBranchesView)

    def test_git(self):
        self.assertCodeViewClass(VCSType.GIT, TargetGitListingView)


class TestPersonDistributionSourcePackageDefaultVCSView(TestCaseWithFactory):
    """Tests that PersonDSP:+code delegates to +git or 404s.

    It can't delegate to +branches, as PersonDSP:+branches doesn't exist.
    """

    layer = DatabaseFunctionalLayer

    def assertCodeViewClass(self, vcs, cls):
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution(vcs=vcs)
        dsp = self.factory.makeDistributionSourcePackage(distribution=distro)
        self.assertEqual(vcs, distro.vcs)
        try:
            view = test_traverse(
                '~%s/%s/+source/%s/+code'
                % (person.name, distro.name, dsp.sourcepackagename.name))[1]
        except NotFound:
            view = None
        self.assertIsInstance(view, cls)

    def test_default_unset(self):
        self.assertCodeViewClass(None, type(None))

    def test_default_bzr(self):
        self.assertCodeViewClass(VCSType.BZR, type(None))

    def test_git(self):
        self.assertCodeViewClass(VCSType.GIT, PersonTargetGitListingView)


class TestDistributionDefaultVCSView(TestCaseWithFactory):
    """Tests that Distribution:+code delegates to +git or +branches."""

    layer = DatabaseFunctionalLayer

    def assertCodeViewClass(self, vcs, cls):
        distro = self.factory.makeDistribution(vcs=vcs)
        self.assertEqual(vcs, distro.vcs)
        view = test_traverse('/%s/+code' % distro.name)[1]
        self.assertIsInstance(view, cls)

    def test_default_unset(self):
        self.assertCodeViewClass(None, DistributionBranchListingView)

    def test_default_bzr(self):
        self.assertCodeViewClass(VCSType.BZR, DistributionBranchListingView)

    def test_git(self):
        self.assertCodeViewClass(VCSType.GIT, PlainGitListingView)
