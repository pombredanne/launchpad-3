# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Define the layers used in Shipit."""

__metaclass__ = type

from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from canonical.launchpad.layers import LaunchpadLayer


class ShipItLayer(LaunchpadLayer):
    """The `ShipIt` layer."""


class ShipItUbuntuLayer(ShipItLayer):
    """The `ShipIt` for Ubuntu layer."""


class ShipItKUbuntuLayer(ShipItLayer):
    """The `ShipIt` for KUbuntu layer."""


class ShipItEdUbuntuLayer(IDefaultBrowserLayer):
    """The `ShipIt` for EdUbuntu layer."""
