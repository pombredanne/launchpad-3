# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for LaunchpadStatisticSet."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatisticSetFacets',
    'LaunchpadStatisticSetSOP',
    ]

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchpadStatisticSet
from canonical.launchpad.browser.launchpad import (
    StructuralObjectPresentation,
    )
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, ContextMenu, custom_widget,
    LaunchpadView, LaunchpadFormView, Link,
    StandardLaunchpadFacets)


class LaunchpadStatisticSetSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return 'Launchpad statistics'

    def listChildren(self, num):
        return []

    def listAltChildren(self, num):
        return None


class LaunchpadStatisticSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for the
    ILaunchpadStatisticSet.
    """

    usedfor = ILaunchpadStatisticSet

    enable_only = ['overview',]


