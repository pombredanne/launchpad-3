# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Define the layers used in Shipit."""

__metaclass__ = type

from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)


class ShipItLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The `ShipIt` layer."""


class ShipItUbuntuLayer(ShipItLayer):
    """The `ShipIt` for Ubuntu layer."""


class ShipItKUbuntuLayer(ShipItLayer):
    """The `ShipIt` for KUbuntu layer."""


class ShipItEdUbuntuLayer(IDefaultBrowserLayer):
    """The `ShipIt` for EdUbuntu layer."""
