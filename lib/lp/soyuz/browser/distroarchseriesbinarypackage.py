# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageNavigation',
    'DistroArchSeriesBinaryPackageView',
    ]

from canonical.launchpad.webapp import (
    ApplicationMenu,
    GetitemNavigation,
    )
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.lazr.utils import smartquote
from lp.soyuz.interfaces.distroarchseriesbinarypackage import (
    IDistroArchSeriesBinaryPackage,
    )


class DistroArchSeriesBinaryPackageOverviewMenu(ApplicationMenu):

    usedfor = IDistroArchSeriesBinaryPackage
    facet = 'overview'
    links = []


class DistroArchSeriesBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroArchSeriesBinaryPackage


class DistroArchSeriesBinaryPackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def page_title(self):
        return smartquote(self.context.title)
