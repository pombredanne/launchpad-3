# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Module that defines the layers/skins used in launchpad, and also utilities
to do with manipulating skins.
"""

__metaclass__ = type

from zope.publisher.interfaces.browser import IBrowserRequest
from zope.interface import directlyProvides, directlyProvidedBy

def setAdditionalSkin(request, skin):
    directlyProvides(request, directlyProvidedBy(request) + skin)

class launchpad(IBrowserRequest):
    """The `launchpad` layer."""

class rosetta(launchpad):
    """The `rosetta` layer."""
