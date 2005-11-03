# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroReleaseSourcePackageReleaseFacets',
    'DistroReleaseSourcePackageReleaseNavigation',
    'DistroReleaseSourcePackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistroReleaseSourcePackageRelease, ILaunchBag)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistroReleaseSourcePackageReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistroReleaseSourcePackageRelease
    enable_only = ['overview', ]



class DistroReleaseSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroReleaseSourcePackageRelease
    facet = 'overview'
    links = []


class DistroReleaseSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistroReleaseSourcePackageRelease


class DistroReleaseSourcePackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

