# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroSeriesSourcePackageReleaseFacets',
    'DistroSeriesSourcePackageReleaseNavigation',
    'DistroSeriesSourcePackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistroSeriesSourcePackageRelease, ILaunchBag)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistroSeriesSourcePackageReleaseFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: A DistroSeriesSourcePackageRelease is not a structural
    # object. It should inherit all navigation from its distro series.

    usedfor = IDistroSeriesSourcePackageRelease
    enable_only = ['overview', ]


class DistroSeriesSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroSeriesSourcePackageRelease
    facet = 'overview'
    links = []


class DistroSeriesSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistroSeriesSourcePackageRelease


class DistroSeriesSourcePackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

