# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Branch targets."""

__metaclass__ = type
__all__ = [
    'branch_to_target',
    'PackageBranchTarget',
    'PersonBranchTarget',
    'ProductBranchTarget',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    BranchVisibilityRule)
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
        from canonical.launchpad.database.branchnamespace import (
            PackageNamespace)
        return PackageNamespace(owner, self.sourcepackage)

    def canCreateBranches(self, user):
        """See `IBranchTarget`."""
        return True

    def areNewBranchesPrivate(self, user):
        """See `IBranchTarget`."""
        return False


class PersonBranchTarget(_BaseBranchTarget):
    implements(IBranchTarget)

    name = '+junk'

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

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from canonical.launchpad.database.branchnamespace import (
            PersonalNamespace)
        return PersonalNamespace(owner)

    def canCreateBranches(self, user):
        """See `IBranchTarget`."""
        return user.inTeam(self.person)

    def areNewBranchesPrivate(self, user):
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
    def name(self):
        """See `IBranchTarget`."""
        return self.product.name

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from canonical.launchpad.database.branchnamespace import (
            ProductNamespace)
        return ProductNamespace(owner, self.product)

    def canCreateBranches(self, user):
        """See `IBranchTarget`."""
        policies = self.product.getBranchVisibilityTeamPolicies()
        for policy in policies:
            if user.inTeam(policy.team):
                return True
        base_rule = self.product.getBaseBranchVisibilityRule()
        return base_rule == BranchVisibilityRule.PUBLIC

    def areNewBranchesPrivate(self, user):
        """See `IBranchTarget`."""
        # If the user is a member of any team that has a PRIVATE or
        # PRIVATE_ONLY rule, then the branches are private.
        policies = self.product.getBranchVisibilityTeamPolicies()
        private = (
            BranchVisibilityRule.PRIVATE,
            BranchVisibilityRule.PRIVATE_ONLY)
        for policy in policies:
            if user.inTeam(policy.team) and policy.rule in private:
                return True
        return False


def get_canonical_url_data_for_target(branch_target):
    """Return the `ICanonicalUrlData` for an `IBranchTarget`."""
    return ICanonicalUrlData(branch_target.context)
