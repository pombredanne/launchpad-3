# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IProcessor, \
                                           IProcessorFamily

class Processor(SQLBase):
    implements(IProcessor)
    _table = 'Processor'

    family = ForeignKey(dbName='family', foreignKey='ProcessorFamily', 
                        notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

class ProcessorFamily(SQLBase):
    implements(IProcessorFamily)
    _table = 'ProcessorFamily'

    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

