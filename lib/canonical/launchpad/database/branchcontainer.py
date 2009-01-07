# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Branch containers."""

__metaclass__ = type
__all__ = [
    'PackageContainer',
    'PersonContainer',
    'ProductContainer',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchcontainer import IBranchContainer


class PackageContainer:
    implements(IBranchContainer)

    def __init__(self, distroseries, sourcepackagename):
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename

    @property
    def name(self):
        """See `IBranchContainer`."""
        return '%s/%s/%s' % (
            self.distroseries.distribution.name,
            self.distroseries.name,
            self.sourcepackagename.name)


class PersonContainer:
    implements(IBranchContainer)

    name = '+junk'

    def __init__(self, person):
        self.person = person


class ProductContainer:
    implements(IBranchContainer)

    def __init__(self, product):
        self.product = product

    @property
    def name(self):
        """See `IBranchContainer`."""
        return self.product.name
