# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['uuidgen', 'Manifest']

from datetime import datetime
import commands

from zope.interface import implements

from sqlobject import MultipleJoin, StringCol

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import IManifest

def uuidgen():
    return commands.getoutput('uuidgen')


class Manifest(SQLBase):
    """A manifest."""

    implements(IManifest)

    _table = 'Manifest'

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    uuid = StringCol(notNull=True, default=uuidgen(), alternateID=True)

    entries = MultipleJoin('ManifestEntry', joinColumn='manifest',
                           orderBy='sequence')

    def __iter__(self):
        return self.entries

