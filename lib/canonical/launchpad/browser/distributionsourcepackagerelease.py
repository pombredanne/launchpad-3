# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageReleaseFacets',
    'DistributionSourcePackageReleaseNavigation',
    'DistributionSourcePackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSourcePackageRelease, ILaunchBag)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistributionSourcePackageReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistributionSourcePackageRelease
    enable_only = ['overview', ]



class DistributionSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackageRelease
    facet = 'overview'
    links = []


class DistributionSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistributionSourcePackageRelease


class DistributionSourcePackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

