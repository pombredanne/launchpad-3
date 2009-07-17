# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of `ICanHasLinkedBranch`."""

__metaclass__ = type
# Don't export anything -- anything you need from this module you can get by
# adapting another object.
__all__ = []

from zope.component import adapts
from zope.interface import implements

from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.distroseries import NoSuchDistroSeries
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage
from lp.soyuz.interfaces.publishing import PackagePublishingPocket


class ProductSeriesLinkedBranch:
    """Implement a linked branch for a product series."""

    adapts(IProductSeries)
    implements(ICanHasLinkedBranch)

    def __init__(self, product_series):
        self._product_series = product_series

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


class ProductLinkedBranch:
    """Implement a linked branch for a product."""

    adapts(IProduct)
    implements(ICanHasLinkedBranch)

    def __init__(self, product):
        self._product = product

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


class PackageLinkedBranch:
    """Implement a linked branch for a source package pocket."""

    adapts(ISuiteSourcePackage)
    implements(ICanHasLinkedBranch)

    def __init__(self, suite_sourcepackage):
        self._suite_sourcepackage = suite_sourcepackage

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


class DistributionPackageLinkedBranch:
    """Implement a linked branch for an `IDistributionSourcePackage`."""

    adapts(IDistributionSourcePackage)
    implements(ICanHasLinkedBranch)

    def __init__(self, distribution_sourcepackage):
        self._distribution_sourcepackage = distribution_sourcepackage

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
