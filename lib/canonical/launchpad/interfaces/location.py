# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211

"""Location interface.

An object can have a location, which includes geographic coordinates and a
time zone.
"""

__metaclass__ = type

__all__ = [
    'ILocation',
    ]

from zope.interface import Attribute, Interface


class ILocation(Interface):
    """A location on Earth."""

    coordinates = Attribute(
        "The (latitude, longitude) this person has given as their default "
        "location, or None")
    time_zone = Attribute(
        "The time zone this person has specified as their default.")
    last_modified_by = Attribute(
        "The person who last provided this location information.")
    date_last_modified = Attribute(
        "The date this information was last updated.")

    def set_location(latitude, longitude, time_zone, user):
        """Provide a location and time zone, by user."""

