# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import ISection

#
#
#

class Section(SQLBase):
    """  Section table SQLObject """
    implements(ISection)
    
    _table = 'Section'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

