# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of `ICanHasLinkedBranch`."""

__metaclass__ = type
# Don't export anything -- anything you need from this module you can get by
# adapting another object.
__all__ = []

from zope.component import adapts
from zope.interface import implements

from lazr.enum import EnumeratedType, Item

from lp.archivepublisher.debversion import Version
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.distroseries import NoSuchDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage


class LinkedBranchOrder(EnumeratedType):
    """An enum used only for ordering."""

    FIRST = Item('Product')
    SECOND = Item('Distribution Source Package')
    THIRD = Item('Product Series')
    FOURTH = Item('Suite Source Package')


class BaseLinkedBranch:
    """Provides the common sorting algorithm."""

    def __cmp__(self, other):
        if not ICanHasLinkedBranch.providedBy(other):
            raise AssertionError("Can't compare with: %r" % other)
        return cmp(self.sort_order, other.sort_order)


class ProductSeriesLinkedBranch(BaseLinkedBranch):
    """Implement a linked branch for a product series."""

    adapts(IProductSeries)
    implements(ICanHasLinkedBranch)

    sort_order = LinkedBranchOrder.THIRD

    def __init__(self, product_series):
        self._product_series = product_series

    def __cmp__(self, other):
        result = super(ProductSeriesLinkedBranch, self).__cmp__(other)
        if result != 0:
            return result
        else:
            return cmp(self._product_series, other._product_series)

    @property
    def branch(self):
        """See `ICanHasLinkedBranch`."""
        return self._product_series.branch

    @property
    def bzr_path(self):
        """See `ICanHasLinkedBranch`."""
        return '/'.join(
            [self._product_series.product.name, self._product_series.name])

    def setBranch(self, branch, registrant=None):
        """See `ICanHasLinkedBranch`."""
        self._product_series.branch = branch


class ProductLinkedBranch(BaseLinkedBranch):
    """Implement a linked branch for a product."""

    adapts(IProduct)
    implements(ICanHasLinkedBranch)

    sort_order = LinkedBranchOrder.FIRST

    def __init__(self, product):
        self._product = product

    def __cmp__(self, other):
        result = super(ProductLinkedBranch, self).__cmp__(other)
        if result != 0:
            return result
        else:
            return cmp(self._product.name, other._product.name)

    @property
    def branch(self):
        """See `ICanHasLinkedBranch`."""
        return ICanHasLinkedBranch(self._product.development_focus).branch

    @property
    def bzr_path(self):
        """See `ICanHasLinkedBranch`."""
        return self._product.name

    def setBranch(self, branch, registrant=None):
        """See `ICanHasLinkedBranch`."""
        ICanHasLinkedBranch(self._product.development_focus).setBranch(
            branch, registrant)


class PackageLinkedBranch(BaseLinkedBranch):
    """Implement a linked branch for a source package pocket."""

    adapts(ISuiteSourcePackage)
    implements(ICanHasLinkedBranch)

    sort_order = LinkedBranchOrder.FOURTH

    def __init__(self, suite_sourcepackage):
        self._suite_sourcepackage = suite_sourcepackage

    def __cmp__(self, other):
        result = super(PackageLinkedBranch, self).__cmp__(other)
        if result != 0:
            return result
        # Next compare the distribution name.
        result = cmp(
            self._suite_sourcepackage.distribution.name,
            other._suite_sourcepackage.distribution.name)
        if result != 0:
            return result
        # For the distroseries, we want to reverse sort the version.
        result = -cmp(
            Version(self._suite_sourcepackage.distroseries.version),
            Version(other._suite_sourcepackage.distroseries.version))
        if result != 0:
            return result
        # Lastly we check the source package name and pocket.
        else:
            my_parts = (
                self._suite_sourcepackage.sourcepackagename.name,
                self._suite_sourcepackage.pocket)
            other_parts = (
                other._suite_sourcepackage.sourcepackagename.name,
                other._suite_sourcepackage.pocket)
            return cmp(my_parts, other_parts)

    @property
    def branch(self):
        """See `ICanHasLinkedBranch`."""
        package = self._suite_sourcepackage.sourcepackage
        pocket = self._suite_sourcepackage.pocket
        return package.getBranch(pocket)

    @property
    def bzr_path(self):
        """See `ICanHasLinkedBranch`."""
        return self._suite_sourcepackage.path

    def setBranch(self, branch, registrant):
        """See `ICanHasLinkedBranch`."""
        package = self._suite_sourcepackage.sourcepackage
        pocket = self._suite_sourcepackage.pocket
        package.setBranch(pocket, branch, registrant)


class DistributionPackageLinkedBranch(BaseLinkedBranch):
    """Implement a linked branch for an `IDistributionSourcePackage`."""

    adapts(IDistributionSourcePackage)
    implements(ICanHasLinkedBranch)

    sort_order = LinkedBranchOrder.SECOND

    def __init__(self, distribution_sourcepackage):
        self._distribution_sourcepackage = distribution_sourcepackage

    def __cmp__(self, other):
        result = super(DistributionPackageLinkedBranch, self).__cmp__(other)
        if result != 0:
            return result
        else:
            my_names = (
                self._distribution_sourcepackage.distribution.name,
                self._distribution_sourcepackage.sourcepackagename.name)
            other_names = (
                other._distribution_sourcepackage.distribution.name,
                other._distribution_sourcepackage.sourcepackagename.name)
            return cmp(my_names, other_names)

    @property
    def branch(self):
        """See `ICanHasLinkedBranch`."""
        development_package = (
            self._distribution_sourcepackage.development_version)
        if development_package is None:
            return None
        suite_sourcepackage = development_package.getSuiteSourcePackage(
            PackagePublishingPocket.RELEASE)
        return ICanHasLinkedBranch(suite_sourcepackage).branch

    @property
    def bzr_path(self):
        """See `ICanHasLinkedBranch`."""
        return '/'.join(
            [self._distribution_sourcepackage.distribution.name,
             self._distribution_sourcepackage.sourcepackagename.name])

    def setBranch(self, branch, registrant):
        """See `ICanHasLinkedBranch`."""
        development_package = (
            self._distribution_sourcepackage.development_version)
        if development_package is None:
            raise NoSuchDistroSeries('no current series')
        suite_sourcepackage = development_package.getSuiteSourcePackage(
            PackagePublishingPocket.RELEASE)
        ICanHasLinkedBranch(suite_sourcepackage).setBranch(branch, registrant)
