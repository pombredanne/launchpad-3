# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageReleaseFacets',
    'DistributionSourcePackageReleaseNavigation',
    'DistributionSourcePackageReleaseShortLink',
    'DistributionSourcePackageReleaseView',
    ]

from zope.component import getUtility

from canonical.launchpad.browser.launchpad import (
    DefaultShortLink)

from canonical.launchpad.interfaces import (
    IDistributionSourcePackageRelease, ILaunchBag, IBuildSet, NotFoundError)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu, Navigation,
    LaunchpadView, GetitemNavigation, stepthrough)


class DistributionSourcePackageReleaseFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: a DistributionSourcePackageRelease is not a structural
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

    @stepthrough('+build')
    def traverse_build(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(IBuildSet).getByBuildID(build_id)
        except NotFoundError:
            return None


class DistributionSourcePackageReleaseView(LaunchpadView):
    pass


class DistributionSourcePackageReleaseShortLink(DefaultShortLink):

    def getLinkText(self):
        return self.context.sourcepackagerelease.version

