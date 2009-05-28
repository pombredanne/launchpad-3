# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageReleaseNavigation',
    'DistroArchSeriesBinaryPackageReleaseView',
    ]

from lp.soyuz.interfaces.distroarchseriesbinarypackagerelease import (
    IDistroArchSeriesBinaryPackageRelease)
from canonical.launchpad.webapp import ApplicationMenu, Navigation


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

