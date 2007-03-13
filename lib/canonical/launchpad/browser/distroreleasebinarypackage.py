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
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation
    )


class DistroReleaseBinaryPackageFacets(StandardLaunchpadFacets):
    # XXX 20061004 mpt: A DistroArchReleaseBinaryPackage is not a structural
    # object. It should inherit all navigation from its distro release.

    usedfor = IDistroReleaseBinaryPackage
    enable_only = ['overview']


class DistroReleaseBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroReleaseBinaryPackage
    facet = 'overview'
    links = []


class DistroReleaseBinaryPackageNavigation(Navigation):

    usedfor = IDistroReleaseBinaryPackage

    def breadcrumb(self):
        return self.context.binarypackagename.name

class DistroReleaseBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


