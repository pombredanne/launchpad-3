# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    ]

from canonical.launchpad.webapp import (
    GetitemNavigation,
    stepthrough,
    )
from lp.registry.interfaces.distribution import IDistribution


class DistributionNavigation(GetitemNavigation):

    usedfor = IDistribution

    @stepthrough('+source')
    def traverse_sources(self, name):
        return self.context.getSourcePackage(name)

