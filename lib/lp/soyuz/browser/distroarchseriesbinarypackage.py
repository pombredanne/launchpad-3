# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroArchSeriesBinaryPackageNavigation',
    'DistroArchSeriesBinaryPackageView',
    ]

from lazr.restful.utils import smartquote

from lp.services.webapp import (
    GetitemNavigation,
    LaunchpadView,
    )
from lp.soyuz.interfaces.distroarchseriesbinarypackage import (
    IDistroArchSeriesBinaryPackage,
    )


class DistroArchSeriesBinaryPackageNavigation(GetitemNavigation):

    usedfor = IDistroArchSeriesBinaryPackage


class DistroArchSeriesBinaryPackageView(LaunchpadView):

    @property
    def page_title(self):
        return smartquote(self.context.title)
