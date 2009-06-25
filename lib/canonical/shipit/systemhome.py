# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Content classes for the 'home page' of shipit."""

__all__ = [
    'ShipItApplication',
    ]

__metaclass__ = type

from zope.interface import implements

from canonical.shipit.interfaces.shipit import IShipItApplication


class ShipItApplication:
    implements(IShipItApplication)
