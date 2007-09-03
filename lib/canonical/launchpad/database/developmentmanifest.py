# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'DevelopmentManifest',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IDevelopmentManifest

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol


class DevelopmentManifest(SQLBase):
    """See IDevelopmentManifest."""

    implements(IDevelopmentManifest)

    _defaultOrder = ['id']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    manifest = ForeignKey(dbName='manifest', foreignKey='Manifest',
        notNull=True)
    distroseries = ForeignKey(dbName='distrorelease',
        foreignKey='DistroSeries', notNull=True)
    sourcepackagename = ForeignKey(dbName='sourcepackagename',
        foreignKey='SourcePackageName', notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)

