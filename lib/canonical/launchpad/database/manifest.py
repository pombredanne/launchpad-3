# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Python imports
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol, StringCol

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IManifest

import commands

def uuidgen():
    return commands.getoutput('uuidgen')


class Manifest(SQLBase):
    """A manifest."""

    implements(IManifest)

    _table = 'Manifest'

    datecreated = DateTimeCol(notNull=True, default=datetime.utcnow())

    uuid = StringCol(notNull=True, default=uuidgen(), alternateID=True)

    entries = MultipleJoin('ManifestEntry', joinColumn='manifest')
    
    def __iter__(self):
        return self.entries


