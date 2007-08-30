# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageFacets',
    'DistroArchSeriesBinaryPackageNavigation',
    'DistroArchSeriesBinaryPackageView',
    ]

from canonical.launchpad.interfaces import IDistroArchSeriesBinaryPackage

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu,
    GetitemNavigation)


class DistroArchSeriesBinaryPackageFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: a DistroArchSeriesBinaryPackage is not a structural
    # object: it should inherit all navigation from its source package.

    usedfor = IDistroArchSeriesBinaryPackage
    enable_only = ['overview',]


class DistroArchSeriesBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackage
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroArchSeriesBinaryPackage

    def breadcrumb(self):
        return self.context.binarypackagename.name


class DistroArchSeriesBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

