# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroSeriesSourcePackageReleaseFacets',
    'DistroSeriesSourcePackageReleaseNavigation',
    'DistroSeriesSourcePackageReleaseView',
    ]

from canonical.launchpad.interfaces import (
    IDistroSeriesSourcePackageRelease)


from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Navigation, stepthrough)
from canonical.launchpad.webapp.publisher import RedirectionView


class DistroSeriesSourcePackageReleaseFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: A DistroSeriesSourcePackageRelease is not a structural
    # object. It should inherit all navigation from its distro series.

    usedfor = IDistroSeriesSourcePackageRelease
    enable_only = ['overview', ]


class DistroSeriesSourcePackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroSeriesSourcePackageRelease
    facet = 'overview'
    links = []


class DistroSeriesSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistroSeriesSourcePackageRelease


    @stepthrough('+files')
    def traverse_files(self, name):
        # If you are like me you'll ask yourself how it can be that we're
        # putting this traversal on IDistroSeriesSourcePackageRelease and
        # using it with sourcepackagerelease-files.pt. The reason is
        # that the canonical_url for SourcePackageRelease is actually an
        # IDistroSeriesSourcePackageRelease page. Weird.
        for file in self.context.files:
            if file.libraryfile.filename == name:
                return RedirectionView(
                    file.libraryfile.http_url, self.request, 301)
        return None


class DistroSeriesSourcePackageReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request


