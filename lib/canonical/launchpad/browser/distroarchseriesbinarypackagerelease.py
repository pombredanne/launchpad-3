# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageReleaseFacets',
    'DistroArchSeriesBinaryPackageReleaseNavigation',
    'DistroArchSeriesBinaryPackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistroArchSeriesBinaryPackageRelease)

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistroArchSeriesBinaryPackageReleaseFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: A DistroArchSeriesBinaryPackageRelease is not a
    # structural object. It should inherit all navigation from its source
    # package.

    usedfor = IDistroArchSeriesBinaryPackageRelease
    enable_only = ['overview', ]


class DistroArchSeriesBinaryPackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackageRelease
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageReleaseNavigation(Navigation):
    usedfor = IDistroArchSeriesBinaryPackageRelease

    def breadcrumb(self):
        return self.context.version


class DistroArchSeriesBinaryPackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

