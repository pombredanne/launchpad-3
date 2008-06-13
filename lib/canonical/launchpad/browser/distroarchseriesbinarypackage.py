# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'distroarchseriesbinarypackage_to_structuralheading',
    'DistroArchSeriesBinaryPackageNavigation',
    'DistroArchSeriesBinaryPackageView',
    ]

from canonical.launchpad.interfaces import (
    IDistroArchSeriesBinaryPackage, IStructuralHeaderPresentation)

from canonical.launchpad.webapp import (
    ApplicationMenu, ContextMenu, GetitemNavigation, Link)


def distroarchseriesbinarypackage_to_structuralheading(dasbp):
    """Adapt an `IDistroArchSeriesBinaryPackage` into an
    `IStructuralHeaderPresentation`.
    """
    return IStructuralHeaderPresentation(dasbp.distroseries)


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

