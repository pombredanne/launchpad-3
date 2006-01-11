# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroReleaseBinaryPackageFacets',
    'DistroReleaseBinaryPackageNavigation',
    'DistroReleaseBinaryPackageView',
    ]

from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget

from zope.component import getUtility

from canonical.launchpad.interfaces import IDistroReleaseBinaryPackage

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu,
    GetitemNavigation)


class DistroReleaseBinaryPackageFacets(StandardLaunchpadFacets):

    usedfor = IDistroReleaseBinaryPackage
    enable_only = ['overview']


class DistroReleaseBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroReleaseBinaryPackage
    facet = 'overview'
    links = []


class DistroReleaseBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroReleaseBinaryPackage

    def breadcrumb(self):
        return self.context.binarypackagename.name

class DistroReleaseBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


