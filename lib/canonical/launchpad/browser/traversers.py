# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

from zope.component import getUtility
from zope.exceptions import NotFoundError

from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IBugTaskSubset, IBugTasksReport,
    IDistributionSet, IProjectSet, IProductSet, ISourcePackageSet,
    IBugTrackerSet, ILaunchBag, ITeamMembershipSubset)
from canonical.launchpad.database import (
    BugAttachmentSet, BugExternalRefSet, BugSubscriptionSet,
    BugWatchSet, BugTasksReport, CVERefSet, BugProductInfestationSet,
    BugPackageInfestationSet, ProductSeriesSet, ProductMilestoneSet,
    PublishedPackageSet, SourcePackageSet)

def traverse_malone_application(malone_application, request, name):
    """Traverse the Malone application object."""
    if name == "bugs":
        return getUtility(IBugSet)
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


def traverseTeam(team, request, name):
    if name == '+members':
        return ITeamMembershipSubset(team)
    
    return None


# XXX: Brad Bollenbach, 2005-06-23: From code review discussion with
# salgado, we decided it would be a good idea to turn this
# database-class using code into adapters from IBug to the appropriate
# *Set (or *Subset, perhaps.)
#
# See https://launchpad.ubuntu.com/malone/bugs/1118.
def traverse_bug(bug, request, name):
    """Traverse an IBug."""
    if name == 'attachments':
        return BugAttachmentSet(bug=bug.id)
    elif name == 'references':
        return BugExternalRefSet(bug=bug.id)
    elif name == 'cverefs':
        return CVERefSet(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionSet(bug=bug.id)
    elif name == 'watches':
        return BugWatchSet(bug=bug.id)
    elif name == 'tasks':
        return getUtility(IBugTaskSet).get(bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationSet(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationSet(bug=bug.id)

    return None


def traverse_bugs(bugcontainer, request, name):
    """Traverse an IBugSet."""
    if name == 'assigned':
        return BugTasksReport()
    else:
        # If the bug is not found, we expect a NotFoundError. If the
        # value of name is not a value that can be used to retrieve a
        # specific bug, we expect a ValueError.
        try:
            return getUtility(IBugSet).get(name)
        except (NotFoundError, ValueError):
            return None


def traverseTeam(team, request, name):
    if name == '+members':
        return ITeamMembershipSubset(team)

    return None
