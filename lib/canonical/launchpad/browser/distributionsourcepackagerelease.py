# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'distributionsourcepackagerelease_to_structuralheading',
    'DistributionSourcePackageReleaseNavigation',
    'DistributionSourcePackageReleaseShortLink',
    ]

from zope.component import getUtility

from canonical.launchpad.browser.launchpad import (
    DefaultShortLink)

from canonical.launchpad.interfaces import (
    IDistributionSourcePackageRelease, ILaunchBag, IBuildSet,
    IStructuralHeaderPresentation, NotFoundError)


from canonical.launchpad.webapp import (
    ApplicationMenu, ContextMenu, Link, Navigation,
    GetitemNavigation, stepthrough)


def distributionsourcepackagerelease_to_structuralheading(dspr):
    """Adapts an `IDistributionSourcePackageRelease` into an
    `IStructuralHeaderPresentation`.
    """
    return IStructuralHeaderPresentation(dspr.sourcepackage)


class DistributionSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackageRelease
    facet = 'overview'
    links = []


class DistributionSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistributionSourcePackageRelease

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


class DistributionSourcePackageReleaseShortLink(DefaultShortLink):

    def getLinkText(self):
        return self.context.sourcepackagerelease.version

