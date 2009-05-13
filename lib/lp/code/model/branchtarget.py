# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Branch targets."""

__metaclass__ = type
__all__ = [
    'branch_to_target',
    'PackageBranchTarget',
    'PersonBranchTarget',
    'ProductBranchTarget',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import isinstance as zope_isinstance

from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchtarget import (
    check_default_stacked_on, IBranchTarget)
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


def branch_to_target(branch):
    """Adapt an IBranch to an IBranchTarget."""
    return branch.target


class _BaseBranchTarget:

    def __eq__(self, other):
        return self.context == other.context

    def __ne__(self, other):
        return self.context != other.context


class PackageBranchTarget(_BaseBranchTarget):
    implements(IBranchTarget)

    def __init__(self, sourcepackage):
        self.sourcepackage = sourcepackage

    @property
    def name(self):
        """See `IBranchTarget`."""
        return self.sourcepackage.path

    @property
    def components(self):
        """See `IBranchTarget`."""
        return [
            self.sourcepackage.distribution,
            self.sourcepackage.distroseries,
            self.sourcepackage,
            ]

    @property
    def context(self):
        """See `IBranchTarget`."""
        return self.sourcepackage

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from lp.code.model.branchnamespace import (
            PackageNamespace)
        return PackageNamespace(owner, self.sourcepackage)

    @property
    def collection(self):
        """See `IBranchTarget`."""
        return getUtility(IAllBranches).inSourcePackage(self.sourcepackage)

    @property
    def default_stacked_on_branch(self):
        """See `IBranchTarget`."""
        return check_default_stacked_on(
            self.sourcepackage.development_version.getBranch(
                PackagePublishingPocket.RELEASE))

    @property
    def default_merge_target(self):
        """See `IBranchTarget`."""
        return self.sourcepackage.getBranch(PackagePublishingPocket.RELEASE)

    @property
    def displayname(self):
        """See `IBranchTarget`."""
        return self.sourcepackage.displayname

    @property
    def supports_merge_proposals(self):
        """See `IBranchTarget`."""
        return True

    def areBranchesMergeable(self, other_target):
        """See `IBranchTarget`."""
        # Branches are mergable into a PackageTarget if the source package
        # name is the same, or the branch is associated with the linked
        # product.
        if zope_isinstance(other_target, PackageBranchTarget):
            my_sourcepackagename = self.context.sourcepackagename
            other_sourcepackagename = other_target.context.sourcepackagename
            return my_sourcepackagename == other_sourcepackagename
        elif zope_isinstance(other_target, ProductBranchTarget):
            # If the sourcepackage has a related product, then branches of
            # that product are mergeable.
            product_series = self.sourcepackage.productseries
            if product_series is None:
                return False
            else:
                return other_target.context == product_series.product
        else:
            return False


class PersonBranchTarget(_BaseBranchTarget):
    implements(IBranchTarget)

    name = '+junk'
    default_stacked_on_branch = None
    default_merge_target = None

    def __init__(self, person):
        self.person = person

    @property
    def components(self):
        """See `IBranchTarget`."""
        return [self.person]

    @property
    def context(self):
        """See `IBranchTarget`."""
        return self.person

    @property
    def displayname(self):
        """See `IBranchTarget`."""
        return "~%s/+junk" % self.person.name

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from lp.code.model.branchnamespace import (
            PersonalNamespace)
        return PersonalNamespace(owner)

    @property
    def collection(self):
        """See `IBranchTarget`."""
        return getUtility(IAllBranches).ownedBy(self.person).isJunk()

    @property
    def supports_merge_proposals(self):
        """See `IBranchTarget`."""
        return False

    def areBranchesMergeable(self, other_target):
        """See `IBranchTarget`."""
        return False


class ProductBranchTarget(_BaseBranchTarget):
    implements(IBranchTarget)

    def __init__(self, product):
        self.product = product

    @property
    def components(self):
        """See `IBranchTarget`."""
        return [self.product]

    @property
    def context(self):
        """See `IBranchTarget`."""
        return self.product

    @property
    def displayname(self):
        """See `IBranchTarget`."""
        return self.product.displayname

    @property
    def name(self):
        """See `IBranchTarget`."""
        return self.product.name

    @property
    def default_stacked_on_branch(self):
        """See `IBranchTarget`."""
        return check_default_stacked_on(self.product.development_focus.branch)

    @property
    def default_merge_target(self):
        """See `IBranchTarget`."""
        return self.product.development_focus.branch

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from lp.code.model.branchnamespace import (
            ProductNamespace)
        return ProductNamespace(owner, self.product)

    @property
    def collection(self):
        """See `IBranchTarget`."""
        return getUtility(IAllBranches).inProduct(self.product)

    @property
    def supports_merge_proposals(self):
        """See `IBranchTarget`."""
        return True

    def areBranchesMergeable(self, other_target):
        """See `IBranchTarget`."""
        # Branches are mergable into a PackageTarget if the source package
        # name is the same, or the branch is associated with the linked
        # product.
        if zope_isinstance(other_target, ProductBranchTarget):
            return self.product == other_target.context
        elif zope_isinstance(other_target, PackageBranchTarget):
            # If the sourcepackage has a related product, and that product is
            # the same as ours, then the branches are mergeable.
            product_series = other_target.context.productseries
            if product_series is None:
                return False
            else:
                return self.product == product_series.product
        else:
            return False


def get_canonical_url_data_for_target(branch_target):
    """Return the `ICanonicalUrlData` for an `IBranchTarget`."""
    return ICanonicalUrlData(branch_target.context)
