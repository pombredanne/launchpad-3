# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for LaunchpadStatisticSet."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatisticSetFacets',
    ]

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchpadStatisticSet
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, ContextMenu, custom_widget,
    LaunchpadView, LaunchpadFormView, Link,
    StandardLaunchpadFacets)


class LaunchpadStatisticSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the
    ILaunchpadStatisticSet.
    """

    usedfor = ILaunchpadStatisticSet

    enable_only = ['overview',]


