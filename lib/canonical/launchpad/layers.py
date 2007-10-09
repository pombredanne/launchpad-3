# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Define the layers used in Launchpad.

Also define utilities that manipulate layers.
"""

__metaclass__ = type

try:
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
except ImportError:
    # This code can go once we've upgraded Zope.
    from zope.publisher.interfaces.browser import IBrowserRequest
    IDefaultBrowserLayer = IBrowserRequest

from zope.interface import directlyProvides, directlyProvidedBy, Interface


def setAdditionalLayer(request, layer):
    directlyProvides(request, directlyProvidedBy(request) + layer)


def setFirstLayer(request, layer):
    directlyProvides(request, layer, directlyProvidedBy(request))


class LaunchpadLayer(IDefaultBrowserLayer):
    """The `LaunchpadLayer` layer."""


class TranslationsLayer(LaunchpadLayer):
    """The `TranslationsLayer` layer."""


class BugsLayer(LaunchpadLayer):
    """The `BugsLayer` layer."""


class CodeLayer(LaunchpadLayer):
    """The `CodeLayer` layer."""


class BlueprintLayer(LaunchpadLayer):
    """The `BlueprintLayer` layer."""
BlueprintsLayer = BlueprintLayer


class AnswersLayer(LaunchpadLayer):
    """The `AnswersLayer` layer."""


class OpenIdLayer(LaunchpadLayer):
    """The `OpenId` layer."""


class DebugLayer(Interface):
    """The `DebugLayer` layer.

    This derives from Interface beacuse it is just a marker that this
    is a debug-related request.
    """


class PageTestLayer(Interface):
    """The `PageTestLayer` layer. (need to register a 404 view for this and
    for the debug page too.  and make the debugview a base class in the
    debug view and make system error, not found and unauthorized and
    forbidden views.

    This layer is applied to the request that is used for running page tests.
    No pages are registered for this layer, but the SystemErrorView base
    class looks at the request to see if it provides this interface.  If so,
    it renders tracebacks as plain text.

    This derives from Interface beacuse it is just a marker that this
    is a pagetest-related request.
    """


class ShipItLayer(LaunchpadLayer):
    """The `ShipIt` layer."""


class ShipItUbuntuLayer(ShipItLayer):
    """The `ShipIt` for Ubuntu layer."""


class ShipItKUbuntuLayer(ShipItLayer):
    """The `ShipIt` for KUbuntu layer."""


class ShipItEdUbuntuLayer(ShipItLayer):
    """The `ShipIt` for EdUbuntu layer."""


class FeedsLayer(LaunchpadLayer):
    """The `Feeds` Layer."""
