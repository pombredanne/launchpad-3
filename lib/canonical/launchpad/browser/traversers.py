# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBugSet, IBugTaskSet, \
     IBugTasksReport, IDistributionSet, IProjectSet, IProductSet, \
     ISourcePackageSet, IBugTrackerSet

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
