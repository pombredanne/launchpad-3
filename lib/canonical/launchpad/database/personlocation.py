# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database class for Person Location.

The location of the person includes their geographic coordinates (latitude
and longitude) and their time zone. We only store this information for
people who have provided it, so we put it in a separate table which
decorates Person.
"""

__metaclass__ = type
__all__ = [
    'PersonLocation',
    ]

from sqlobject import FloatCol, ForeignKey, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ILocation
from canonical.launchpad.validators.person import validate_public_person


class PersonLocation(SQLBase):
    """A person's location."""

    _defaultOrder = ['id']

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True, unique=True)
    latitude = FloatCol(notNull=False)
    longitude = FloatCol(notNull=False)
    time_zone = StringCol(notNull=True)
    last_modified_by = ForeignKey(
        dbName='last_modified_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    date_last_modified = UtcDateTimeCol(notNull=True, default=UTC_NOW)


class PersonLocationAdapter:

    implements(ILocation)
    
    def __init__(self, context):
        self.person = context
        self.location = PersonLocation.selectOneBy(person=context.id)

    @property
    def date_created(self):
        if self.location is None:
            return None
        return self.location.date_created

    @property
    def time_zone(self):
        if self.location is None:
            return None
        return self.location.time_zone

    @property
    def latitude(self):
        if self.location is None:
            return None
        return self.location.latitude

    @property
    def longitude(self):
        if self.location is None:
            return None
        return self.location.longitude

    @property
    def last_modified_by(self):
        """See `ILocation`."""
        if self.location is None:
            return None
        return self.location.last_modified_by

    @property
    def date_last_modified(self):
        """See `ILocation`."""
        if self.location is None:
            return None
        return self.location.date_last_modified

    @property
    def coordinates(self):
        """See `ILocation`."""
        if self.location is None:
            return None
        if self.location.latitude is None or \
           self.location.longitude is None:
            return None
        return (self.location.latitude, self.location.longtitude)

    def set_location(self, latitude, longitude, time_zone, user):
        """See `ILocation`."""
        if self.location is not None:
            self.location.time_zone = time_zone
            self.location.latitude = latitude
            self.location.longitude = longitude
            self.location.last_modified_by = user
            self.location.date_last_modified = UTC_NOW
        else:
            self.location = PersonLocation(
                person=self.person,
                time_zone=time_zone,
                latitude=latitude,
                longitude=longitude,
                last_modified_by=user)

