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

import pytz
from sqlobject import FloatCol, ForeignKey, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.location import ILocationRecord
from canonical.launchpad.validators.person import validate_public_person
from canonical.launchpad.webapp.errorlog import report_timezone_oops


def validate_timezone(self, attr, value):
    """Checks that the timzone file exists.

    :raises KeyError or IOError if the timezone does not exist.
    """
    # pylint: disable-msg=W0702
    # Disabling pylint warning for "except:" block which
    # doesn't specify an exception.
    try:
        pytz.timezone(value)
    except:
        message = "Invalid timezone (%s) for %r.%s" % (value, self, attr)
        report_timezone_oops(message)
        raise ValueError, message
    return value


class PersonLocation(SQLBase):
    """A person's location."""

    implements(ILocationRecord)
 
    _defaultOrder = ['id']

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True, unique=True)
    latitude = FloatCol(notNull=False)
    longitude = FloatCol(notNull=False)
    time_zone = StringCol(notNull=True, storm_validator=validate_timezone)
    last_modified_by = ForeignKey(
        dbName='last_modified_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    date_last_modified = UtcDateTimeCol(notNull=True, default=UTC_NOW)


