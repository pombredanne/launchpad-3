# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroSeriesBinaryPackageFacets',
    'DistroSeriesBinaryPackageNavigation',
    'DistroSeriesBinaryPackageView',
    ]

from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget

from zope.component import getUtility

from canonical.launchpad.interfaces import IDistroSeriesBinaryPackage

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation
    )


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

    def breadcrumb(self):
        return self.context.binarypackagename.name

class DistroSeriesBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


