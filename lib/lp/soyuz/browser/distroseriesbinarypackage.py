# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroSeriesBinaryPackageBreadcrumbBuilder',
    'DistroSeriesBinaryPackageFacets',
    'DistroSeriesBinaryPackageNavigation',
    'DistroSeriesBinaryPackageView',
    ]

from lp.soyuz.interfaces.distroseriesbinarypackage import (
    IDistroSeriesBinaryPackage)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Navigation)
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder


class DistroSeriesBinaryPackageFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: A DistroArchSeriesBinaryPackage is not a structural
    # object. It should inherit all navigation from its distro series.

    usedfor = IDistroSeriesBinaryPackage
    enable_only = ['overview']


class DistroSeriesBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroSeriesBinaryPackage
    facet = 'overview'
    links = []


class DistroSeriesBinaryPackageNavigation(Navigation):

    usedfor = IDistroSeriesBinaryPackage


class DistroSeriesBinaryPackageBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IDistroSeriesBinaryPackage`."""
    @property
    def text(self):
        return self.context.binarypackagename.name


class DistroSeriesBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


