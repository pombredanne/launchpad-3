# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive']

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IArchive


class Archive(SQLBase):
    implements(IArchive)
    _table = 'Archive'
    _defaultOrder = 'id'

