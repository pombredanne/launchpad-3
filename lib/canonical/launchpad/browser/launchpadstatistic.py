# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for LaunchpadStatisticSet."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatisticSetFacets',
    ]

from canonical.launchpad.interfaces import ILaunchpadStatisticSet
from canonical.launchpad.webapp import StandardLaunchpadFacets


class LaunchpadStatisticSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the
    ILaunchpadStatisticSet.
    """

    usedfor = ILaunchpadStatisticSet

    enable_only = ['overview',]


