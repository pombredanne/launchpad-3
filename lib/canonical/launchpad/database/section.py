# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Section']

from zope.interface import implements

from sqlobject import StringCol

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import ISection


class Section(SQLBase):
    """Section table SQLObject."""
    implements(ISection)

    _table = 'Section'

    name = StringCol(notNull=True)

