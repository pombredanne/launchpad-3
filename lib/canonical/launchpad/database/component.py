# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Component']

from zope.interface import implements

from sqlobject import StringCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IComponent


class Component(SQLBase):
    """Component table SQLObject """
    implements(IComponent)

    _table = 'Component'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

