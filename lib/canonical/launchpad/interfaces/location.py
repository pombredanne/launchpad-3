# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Location interface.

An object can have a location, which includes geographic coordinates and a
time zone.
"""

__metaclass__ = type

__all__ = [
    'IHasLocation',
    'ILocationRecord',
    'IObjectWithLocation',
    'ISetLocation',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Float

from canonical.launchpad import _
from canonical.lazr.interface import copy_field
from canonical.lazr.rest.declarations import (
   call_with, export_write_operation, exported, operation_parameters,
   REQUEST_USER)


class IHasLocation(Interface):
    """An interface supported by objects with a defined location."""

    latitude = exported(
        Float(required=False, title=_("The latitude of this object.")))
    longitude = exported(
        Float(required=False, title=_("The longitude of this object.")))
    time_zone = exported(
        Choice(required=False, title=_('The time zone of this object.'),
        vocabulary='TimezoneName'))


class ISetLocation(Interface):
    """An interface for setting the location and time zone of an object."""

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        latitude=copy_field(IHasLocation['latitude']),
        longitude=copy_field(IHasLocation['longitude']),
        time_zone=copy_field(IHasLocation['time_zone']))
    @export_write_operation()
    def setLocation(latitude, longitude, time_zone, user):
        """Specify the location and time zone of a person."""


class IObjectWithLocation(Interface):
    """An interface supported by objects with a defined location."""

    location = Attribute("An ILocation for this object.")


class ILocationRecord(IHasLocation):
    """A location record, which may be attached to a particular object.
    
    The location record contains additional information such as the date the
    location data was recorded, and by whom.
    """

    last_modified_by = Attribute(
        "The person who last provided this location information.")
    date_last_modified = Datetime(
        title=_("The date this information was last updated."))

