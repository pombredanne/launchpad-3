# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.model.branchtarget import (
    check_default_stacked_on,
    PackageBranchTarget, PersonBranchTarget, ProductBranchTarget)
from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.branchtarget import IBranchTarget
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
        default_branch.startMirroring()
        default_branch.mirrorComplete(self.factory.getUniqueString())
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        run_with_login(
            ubuntu_branches.teamowner,
            development_package.setBranch,
            PackagePublishingPocket.RELEASE, default_branch,
            ubuntu_branches.teamowner)
        self.assertEqual(default_branch, target.default_stacked_on_branch)

    def test_displayname(self):
        # The display name of a source package target is the display name of
        # the source package.
        target = IBranchTarget(self.original)
        self.assertEqual(self.original.displayname, target.displayname)

    def test_collection(self):
        # The collection attribute should return an IBranchCollection filtered
        # by a single package branch.
        self.assertEqual(self.target.collection.getBranches().count(), 0)
        package_branch = self.factory.makePackageBranch(
            sourcepackage=self.original)
        branches = self.target.collection.getBranches()
        self.assertEqual(branches.count(), 1)
        self.assertTrue(package_branch in branches)


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

    def test_displayname(self):
        # The display name of a person branch target is ~$USER/+junk.
        target = IBranchTarget(self.original)
        self.assertEqual('~%s/+junk' % self.original.name, target.displayname)

    def test_collection(self):
        # The collection attribute should return an IBranchCollection filtered
        # by a single package branch.
        self.assertEqual(self.target.collection.getBranches().count(), 0)
        package_branch = self.factory.makeBranch(
            owner=self.original)
        branches = self.target.collection.getBranches()
        self.assertEqual(branches.count(), 1)
        self.assertTrue(package_branch in branches)


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
        removeSecurityProxy(product).development_focus.branch = branch

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

    def test_displayname(self):
        # The display name of a product branch target is the display name of
        # the product.
        target = IBranchTarget(self.original)
        self.assertEqual(self.original.displayname, target.displayname)

    def test_collection(self):
        # The collection attribute should return an IBranchCollection filtered
        # by a single package branch.
        self.assertEqual(self.target.collection.getBranches().count(), 0)
        package_branch = self.factory.makeBranch(
            product=self.original)
        branches = self.target.collection.getBranches()
        self.assertEqual(branches.count(), 1)
        self.assertTrue(package_branch in branches)


class TestCheckDefaultStackedOnBranch(TestCaseWithFactory):
    """Only certain branches are allowed to be default stacked-on branches."""

    layer = DatabaseFunctionalLayer

    def test_none(self):
        # `check_default_stacked_on` returns None if passed None.
        self.assertIs(None, check_default_stacked_on(None))

    def test_unmirrored(self):
        # `check_default_stacked_on` returns None if passed an unmirrored
        # banch. This is because we don't want to stack things on unmirrored
        # branches.
        branch = self.factory.makeAnyBranch()
        self.assertIs(None, check_default_stacked_on(branch))

    def test_remote(self):
        # `check_default_stacked_on` returns None if passed a remote branch.
        # We have no Bazaar data for remote branches, so stacking on one is
        # futile.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.REMOTE)
        self.assertIs(None, check_default_stacked_on(branch))

    def test_remote_thats_been_mirrored(self):
        # Although REMOTE branches are not generally ever mirrored, it's
        # possible for a branch to be turned into a REMOTE branch later in
        # life.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
        branch.startMirroring()
        branch.mirrorComplete(self.factory.getUniqueString())
        removeSecurityProxy(branch).branch_type = BranchType.REMOTE
        self.assertIs(None, check_default_stacked_on(branch))

    def test_invisible(self):
        # `check_default_stacked_on` returns None for branches invisible to
        # the current user.
        branch = self.factory.makeAnyBranch(private=True)
        self.assertIs(None, check_default_stacked_on(branch))

    def test_invisible_been_mirrored(self):
        # `check_default_stacked_on` returns None for branches invisible to
        # the current user, even if those branches have already been mirrored.
        branch = self.factory.makeAnyBranch(private=True)
        naked_branch = removeSecurityProxy(branch)
        naked_branch.startMirroring()
        naked_branch.mirrorComplete(self.factory.getUniqueString())
        self.assertIs(None, check_default_stacked_on(branch))

    def test_been_mirrored(self):
        # `check_default_stacked_on` returns None if passed a remote branch.
        # We have no Bazaar data for remote branches, so stacking on one is
        # futile.
        branch = self.factory.makeAnyBranch()
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertEqual(branch, check_default_stacked_on(branch))


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
