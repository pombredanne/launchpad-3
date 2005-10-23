# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Processor', 'ProcessorFamily']

from zope.interface import implements

from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IProcessor, IProcessorFamily

class Processor(SQLBase):
    implements(IProcessor)
    _table = 'Processor'

    family = ForeignKey(dbName='family', foreignKey='ProcessorFamily',
                        notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)


class ProcessorFamily(SQLBase):
    implements(IProcessorFamily)
    _table = 'ProcessorFamily'

    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)

    processors = MultipleJoin('Processor', joinColumn='family')

