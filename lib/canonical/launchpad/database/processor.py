# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Processor', 'ProcessorFamily', 'ProcessorFamilySet']

from zope.component import getUtility
from zope.interface import implements

from sqlobject import StringCol, ForeignKey, SQLMultipleJoin

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IProcessor, IProcessorFamily, IProcessorFamilySet)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


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

    processors = SQLMultipleJoin('Processor', joinColumn='family')


class ProcessorFamilySet:
    implements(IProcessorFamilySet)
    def getByName(self, name):
        """Please see `IProcessorFamilySet`."""
        # Please note that ProcessorFamily.name is unique i.e. the database
        # will return a result set that's either empty or contains just one
        # ProcessorFamily row.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        rset = store.find(ProcessorFamily, name=name)
        if rset.count() == 0:
            return None
        else:
            return rset[0]
