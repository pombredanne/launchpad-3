# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Module that defines the layers used in launchpad, and also utilities
to do with manipulating layers.
"""

__metaclass__ = type

from zope.publisher.interfaces.browser import IBrowserRequest
from zope.interface import directlyProvides, directlyProvidedBy

def setAdditionalLayer(request, layer):
    directlyProvides(request, directlyProvidedBy(request) + layer)

def setFirstLayer(request, layer):
    directlyProvides(request, layer, directlyProvidedBy(request))

class LaunchpadLayer(IBrowserRequest):
    """The `LaunchpadLayer` layer."""

class RosettaLayer(LaunchpadLayer):
    """The `RosettaLayer` layer."""

class UbuntuLinuxLayer(IBrowserRequest):
    """The `UbuntuLinuxLayer` layer."""

class DebugLayer(IBrowserRequest):
    """The `DebugLayer` layer."""
