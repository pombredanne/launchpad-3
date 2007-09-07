# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['License']

from zope.interface import implements

from sqlobject import StringCol

from canonical.database.datetimecol import UtcDateTimeCol

from canonical.database.constants import UTC_NOW

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import ILicense, ILicenseSet

class LicenseSet:
    implements(ILicenseSet)

    def __iter__(self):
        """See `ILicenseSet`."""
        return iter(License.select(orderBy='id'))

    def get(self, licenseid):
        """See `ILicenseSet`."""
        try:
            return License.get(licenseid)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate license with ID %s." % str(licenseid))


class License(SQLBase):
    """A Software License."""

    implements(ILicense)

    _table='License'

    legalese = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(dbName='date_created', notNull=True,
                                 default=UTC_NOW)



