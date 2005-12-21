# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchReleaseBinaryPackageFacets',
    'DistroArchReleaseBinaryPackageNavigation',
    'DistroArchReleaseBinaryPackageView',
    ]

from canonical.launchpad.interfaces import IDistroArchReleaseBinaryPackage

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu,
    GetitemNavigation)


class DistroArchReleaseBinaryPackageFacets(StandardLaunchpadFacets):

    usedfor = IDistroArchReleaseBinaryPackage
    enable_only = ['overview',]


class DistroArchReleaseBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchReleaseBinaryPackage
    facet = 'overview'
    links = []


class DistroArchReleaseBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroArchReleaseBinaryPackage

    def breadcrumb(self):
        return self.context.binarypackagename.name


class DistroArchReleaseBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

