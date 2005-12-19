# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackageReleaseFacets',
    'DistroArchReleaseBinaryPackageReleaseNavigation',
    'DistroArchReleaseBinaryPackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistroArchReleaseBinaryPackageRelease)

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistroArchReleaseBinaryPackageReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistroArchReleaseBinaryPackageRelease
    enable_only = ['overview', ]



class DistroArchReleaseBinaryPackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchReleaseBinaryPackageRelease
    facet = 'overview'
    links = []


class DistroArchReleaseBinaryPackageReleaseNavigation(Navigation):
    usedfor = IDistroArchReleaseBinaryPackageRelease

    def breadcrumb(self):
        return self.context.version


class DistroArchReleaseBinaryPackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

