# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Module that defines the layers used in launchpad, and also utilities
to do with manipulating layers.
"""

__metaclass__ = type
try:
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
except ImportError:
    # This code can go once we've upgraded Zope.
    from zope.publisher.interfaces.browser import IBrowserRequest
    IDefaultBrowserLayer = IBrowserRequest

from zope.interface import directlyProvides, directlyProvidedBy

def setAdditionalLayer(request, layer):
    directlyProvides(request, directlyProvidedBy(request) + layer)

def setFirstLayer(request, layer):
    directlyProvides(request, layer, directlyProvidedBy(request))

class LaunchpadLayer(IDefaultBrowserLayer):
    """The `LaunchpadLayer` layer."""

class RosettaLayer(LaunchpadLayer):
    """The `RosettaLayer` layer."""

class MaloneLayer(LaunchpadLayer):
    """The `MaloneLayer` layer."""

class BazaarLayer(LaunchpadLayer):
    """The `BazaarLayer` layer."""

class UbuntuLinuxLayer(IDefaultBrowserLayer):
    """The `UbuntuLinuxLayer` layer."""

class DebugLayer(IDefaultBrowserLayer):
    """The `DebugLayer` layer."""
