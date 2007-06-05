# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageReleaseFacets',
    'DistributionSourcePackageReleaseNavigation',
    'DistributionSourcePackageReleaseShortLink',
    'DistributionSourcePackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.browser.launchpad import DefaultShortLink

from canonical.launchpad.interfaces import (
    IDistributionSourcePackageRelease, ILaunchBag)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation)


class DistributionSourcePackageReleaseFacets(StandardLaunchpadFacets):
    # XXX 20061004 mpt: a DistributionSourcePackageRelease is not a structural
    # object: it should inherit all navigation from its source package.

    usedfor = IDistributionSourcePackageRelease
    enable_only = ['overview', ]


class DistributionSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackageRelease
    facet = 'overview'
    links = []


class DistributionSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistributionSourcePackageRelease

    def breadcrumb(self):
        return self.context.version

class DistributionSourcePackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


class DistributionSourcePackageReleaseShortLink(DefaultShortLink):

    def getLinkText(self):
        return self.context.sourcepackagerelease.version
