# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageNavigation',
    'DistroArchSeriesBinaryPackageView',
    ]

from lp.soyuz.interfaces.distroarchseriesbinarypackage import (
    IDistroArchSeriesBinaryPackage)
from canonical.launchpad.webapp import ApplicationMenu, GetitemNavigation


class DistroArchSeriesBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackage
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroArchSeriesBinaryPackage


class DistroArchSeriesBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

