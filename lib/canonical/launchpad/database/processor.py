# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func

from canonical.database.sqlbase import SQLBase, quote

# interfaces and database 
from canonical.launchpad.interfaces import IProcessor, \
                                           IProcessorFamily

class SoyuzProcessor(SQLBase):
    implements(IProcessor)

    _table = 'Processor'
    _columns = [
        ForeignKey(name='family', dbName='family',
                   foreignKey='SoyuzProcessorFamily', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

class SoyuzProcessorFamily(SQLBase):
    implements(IProcessorFamily)

    _table = 'ProcessorFamily'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

