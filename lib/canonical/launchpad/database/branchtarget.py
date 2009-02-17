# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Branch targets."""

__metaclass__ = type
__all__ = [
    'PackageContainer',
    'PersonContainer',
    'ProductContainer',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchtarget import IBranchTarget


class PackageContainer:
    implements(IBranchTarget)

    def __init__(self, sourcepackage):
        self.sourcepackage = sourcepackage

    @property
    def name(self):
        """See `IBranchTarget`."""
        return self.sourcepackage.path

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from canonical.launchpad.database.branchnamespace import (
            PackageNamespace)
        return PackageNamespace(owner, self.sourcepackage)


class PersonContainer:
    implements(IBranchTarget)

    name = '+junk'

    def __init__(self, person):
        self.person = person

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from canonical.launchpad.database.branchnamespace import (
            PersonalNamespace)
        return PersonalNamespace(owner)


class ProductContainer:
    implements(IBranchTarget)

    def __init__(self, product):
        self.product = product

    @property
    def name(self):
        """See `IBranchTarget`."""
        return self.product.name

    def getNamespace(self, owner):
        """See `IBranchTarget`."""
        from canonical.launchpad.database.branchnamespace import (
            ProductNamespace)
        return ProductNamespace(owner, self.product)
