# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import StringCol, MultipleJoin
from canonical.database.sqlbase import SQLBase

# canonical imports
from canonical.launchpad.interfaces import IPOTemplateName

class POTemplateName(SQLBase):
    implements(IPOTemplateName)

    _table = 'POTemplateName'

    name = StringCol(dbName='name', notNull=True, unique=True, alternateID=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    potemplates = MultipleJoin('POTemplate', joinColumn='potemplatename')

