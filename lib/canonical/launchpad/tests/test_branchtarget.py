# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branchtarget import (
    PackageBranchTarget, PersonBranchTarget, ProductBranchTarget)
from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.testing import run_with_login, TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer


class BaseBranchTargetTests:

    def test_provides_IPrimaryContext(self):
        self.assertProvides(self.target, IPrimaryContext)

    def test_context(self):
        # IBranchTarget.context is the original object.
        self.assertEqual(self.original, self.target.context)

    def test_canonical_url(self):
        # The canonical URL of a branch target is the canonical url of its
        # context.
        self.assertEqual(
            canonical_url(self.original), canonical_url(self.target))


class TestPackageBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeSourcePackage()
        self.target = PackageBranchTarget(self.original)

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        self.assertEqual(self.original.path, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(self.original, namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(self.target, PackageBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual(
            [self.original.distribution, self.original.distroseries,
             self.original],
            list(target.components))

    def test_default_stacked_on_branch(self):
        # The default stacked-on branch for a source package is the branch
        # linked to the release pocket of the current series of that package.
        target = IBranchTarget(self.original)
        development_package = self.original.development_version
        default_branch = self.factory.makePackageBranch(
            sourcepackage=development_package)
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        run_with_login(
            ubuntu_branches.teamowner,
            development_package.setBranch,
            PackagePublishingPocket.RELEASE, default_branch,
            ubuntu_branches.teamowner)
        self.assertEqual(default_branch, target.default_stacked_on_branch)


class TestPersonBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makePerson()
        self.target = PersonBranchTarget(self.original)

    def test_name(self):
        # The name of a junk context is '+junk'.
        self.assertEqual('+junk', self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        namespace = self.target.getNamespace(self.original)
        self.assertEqual(namespace.owner, self.original)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, PersonBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual([self.original], list(target.components))

    def test_default_stacked_on_branch(self):
        # Junk branches are not stacked by default, ever.
        target = IBranchTarget(self.original)
        self.assertIs(None, target.default_stacked_on_branch)


class TestProductBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeProduct()
        self.target = ProductBranchTarget(self.original)

    def test_name(self):
        self.assertEqual(self.original.name, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(namespace.product, self.original)
        self.assertEqual(namespace.owner, person)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, ProductBranchTarget)

    def test_components(self):
        target = IBranchTarget(self.original)
        self.assertEqual([self.original], list(target.components))

    def test_default_stacked_on_branch_no_dev_focus(self):
        # The default stacked-on branch for a product target that has no
        # development focus is None.
        target = IBranchTarget(self.original)
        self.assertIs(None, target.default_stacked_on_branch)

    def _setDevelopmentFocus(self, product, branch):
        removeSecurityProxy(product).development_focus.user_branch = branch

    def test_default_stacked_on_branch_unmirrored_dev_focus(self):
        # If the development focus hasn't been mirrored, then don't use it as
        # the default stacked-on branch.
        branch = self.factory.makeProductBranch(product=self.original)
        self._setDevelopmentFocus(self.original, branch)
        target = IBranchTarget(self.original)
        self.assertIs(None, target.default_stacked_on_branch)

    def test_default_stacked_on_branch_has_been_mirrored(self):
        # If the development focus has been mirrored, then use it as the
        # default stacked-on branch.
        branch = self.factory.makeProductBranch(product=self.original)
        self._setDevelopmentFocus(self.original, branch)
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        target = IBranchTarget(self.original)
        self.assertEqual(branch, target.default_stacked_on_branch)


class TestPrimaryContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_package_branch(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_product_branch(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
