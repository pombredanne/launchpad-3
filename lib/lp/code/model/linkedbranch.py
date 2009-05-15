# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of `ICanHasLinkedBranch`."""

__metaclass__ = type
# Don't export anything -- anything you need from this module you can get by
# adapting another object.
__all__ = []

from zope.component import adapter, getSiteManager
from zope.interface import implementer, implements

from lp.code.interfaces.branchlookup import ICanHasLinkedBranch
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage


class HasLinkedBranch:
    """A thing that has a linked branch."""

    implements(ICanHasLinkedBranch)

    def __init__(self, branch):
        self.branch = branch


@adapter(IProductSeries)
@implementer(ICanHasLinkedBranch)
def product_series_linked_branch(product_series):
    """The series branch of a product series is its linked branch."""
    return HasLinkedBranch(product_series.branch)


@adapter(IProduct)
@implementer(ICanHasLinkedBranch)
def product_linked_branch(product):
    """The series branch of a product's development focus is its branch."""
    return HasLinkedBranch(product.development_focus.branch)


@adapter(ISuiteSourcePackage)
@implementer(ICanHasLinkedBranch)
def package_linked_branch(suite_sourcepackage):
    package = suite_sourcepackage.sourcepackage
    pocket = suite_sourcepackage.pocket
    return HasLinkedBranch(package.getBranch(pocket))


sm = getSiteManager()
sm.registerAdapter(product_series_linked_branch)
sm.registerAdapter(product_linked_branch)
sm.registerAdapter(package_linked_branch)
