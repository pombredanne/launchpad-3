# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'distroarchseriesbinarypackagerelease_to_structuralheading',
    'DistroArchSeriesBinaryPackageReleaseNavigation',
    'DistroArchSeriesBinaryPackageReleaseView',
    ]

from canonical.launchpad.interfaces import (
    IDistroArchSeriesBinaryPackageRelease, IStructuralHeaderPresentation)

from canonical.launchpad.webapp import ApplicationMenu, Navigation


def distroarchseriesbinarypackagerelease_to_structuralheading(dasbpr):
    """Adapt an `IDistroArchSeriesBinaryPackageRelease` into an
    `IStructuralHeaderPresentation`.
    """
    return IStructuralHeaderPresentation(dasbpr.distroseries)


class DistroArchSeriesBinaryPackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackageRelease
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageReleaseNavigation(Navigation):
    usedfor = IDistroArchSeriesBinaryPackageRelease


class DistroArchSeriesBinaryPackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

