# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroSeriesBinaryPackageBreadcrumb',
    'DistroSeriesBinaryPackageNavigation',
    'DistroSeriesBinaryPackageView',
    ]

from lazr.restful.utils import smartquote

from lp.services.webapp import (
    LaunchpadView,
    Navigation,
    )
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.soyuz.interfaces.distroseriesbinarypackage import (
    IDistroSeriesBinaryPackage,
    )


class DistroSeriesBinaryPackageNavigation(Navigation):

    usedfor = IDistroSeriesBinaryPackage


class DistroSeriesBinaryPackageBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `IDistroSeriesBinaryPackage`."""
    @property
    def text(self):
        return self.context.binarypackagename.name


class DistroSeriesBinaryPackageView(LaunchpadView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def page_title(self):
        return smartquote(self.context.title)
