# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IBugTaskSubset, IBugTasksReport,
    IDistributionSet, IProjectSet, IProductSet, ISourcePackageSet,
    IBugTrackerSet, ILaunchBag)

from canonical.launchpad.database import (
    ProductSeriesSet, ProductMilestoneSet, PublishedPackageSet,
    SourcePackageSet)

def traverse_malone_application(malone_application, request, name):
    """Traverse the Malone application object."""
    if name == "bugs":
        return getUtility(IBugSet)
    elif name == "tasks":
        return getUtility(IBugTaskSet)
    elif name == "assigned":
        return getUtility(IBugTasksReport)
    elif name == "distros":
        return getUtility(IDistributionSet)
    elif name == "projects":
        return getUtility(IProjectSet)
    elif name == "products":
        return getUtility(IProductSet)
    elif name == "packages":
        return getUtility(ISourcePackageSet)
    elif name == "bugtrackers":
        return getUtility(IBugTrackerSet)

    return None


def traverse_product(product, request, name):
    """Traverse an IProduct."""
    if name == '+series':
        return ProductSeriesSet(product=product)
    elif name == '+milestones':
        return ProductMilestoneSet(product=product)
    elif name == '+bugs':
        return IBugTaskSubset(product)
    else:
        return product.getRelease(name)

    return None


def traverse_distribution(distribution, request, name):
    """Traverse an IDistribution."""
    if name == '+packages':
        return PublishedPackageSet()
    elif name == '+bugs':
        return IBugTaskSubset(distribution)
    else:
        return getUtility(ILaunchBag).distribution[name]

    return None


def traverse_distrorelease(distrorelease, request, name):
    """Traverse an IDistroRelease."""
    if name == '+sources':
        return SourcePackageSet(distrorelease=distrorelease)
    elif name  == '+packages':
        return PublishedPackageSet()
    elif name == '+bugs':
        return IBugTaskSubset(distrorelease)
    else:
        return distrorelease[name]

