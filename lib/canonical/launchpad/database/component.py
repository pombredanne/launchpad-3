# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IComponent

#
#
#

class Component(SQLBase):
    """  Component table SQLObject """
    implements(IComponent)

    _table = 'Component'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

