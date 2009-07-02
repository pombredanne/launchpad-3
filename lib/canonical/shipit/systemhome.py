# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Content classes for the 'home page' of shipit."""

__all__ = [
    'ShipItApplication',
    ]

__metaclass__ = type

from zope.interface import implements

from canonical.shipit.interfaces.shipit import IShipItApplication


class ShipItApplication:
    implements(IShipItApplication)
