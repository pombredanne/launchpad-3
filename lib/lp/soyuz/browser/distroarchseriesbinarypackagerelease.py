# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageReleaseBreadcrumb',
    'DistroArchSeriesBinaryPackageReleaseNavigation',
    'DistroArchSeriesBinaryPackageReleaseView',
    ]

from lazr.restful.utils import smartquote

from canonical.launchpad.webapp import (
    ApplicationMenu,
    LaunchpadView,
    Navigation,
    )
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from lp.soyuz.interfaces.distroarchseriesbinarypackagerelease import (
    IDistroArchSeriesBinaryPackageRelease,
    )


class DistroArchSeriesBinaryPackageReleaseBreadcrumb(Breadcrumb):
    """A breadcrumb for `DistroArchSeriesBinaryPackageRelease`."""

    @property
    def text(self):
        return self.context.version


class DistroArchSeriesBinaryPackageReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackageRelease
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageReleaseNavigation(Navigation):
    usedfor = IDistroArchSeriesBinaryPackageRelease


class DistroArchSeriesBinaryPackageReleaseView(LaunchpadView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def page_title(self):
        return smartquote(self.context.title)
