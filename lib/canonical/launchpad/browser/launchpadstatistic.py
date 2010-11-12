# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for LaunchpadStatisticSet."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatisticSet',
    'LaunchpadStatisticSetFacets',
    ]

from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet,
    )
from canonical.launchpad.webapp import (
    LaunchpadView,
    StandardLaunchpadFacets,
    )


class LaunchpadStatisticSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the
    ILaunchpadStatisticSet.
    """

    usedfor = ILaunchpadStatisticSet

    enable_only = ['overview',]


class LaunchpadStatisticSet(LaunchpadView):
    label = page_title = "Launchpad statistics"
