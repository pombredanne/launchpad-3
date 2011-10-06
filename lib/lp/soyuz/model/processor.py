# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Processor', 'ProcessorFamily', 'ProcessorFamilySet']

from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    StringCol,
    )
from storm.locals import Bool
from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.soyuz.interfaces.processor import (
    IProcessor,
    IProcessorFamily,
    IProcessorFamilySet,
    IProcessorSet,
    ProcessorNotFound,
    )


class Processor(SQLBase):
    implements(IProcessor)
    _table = 'Processor'

    family = ForeignKey(dbName='family', foreignKey='ProcessorFamily',
                        notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)

    def __repr__(self):
        return "<Processor %r>" % self.title


class ProcessorSet:
    """See `IProcessorSet`."""
    implements(IProcessorSet)

    def getByName(self, name):
        """See `IProcessorSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        processor = store.find(Processor, Processor.name == name).one()
        if processor is None:
            raise ProcessorNotFound(name)
        return processor

    def getAll(self):
        """See `IProcessorSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(Processor)


class ProcessorFamily(SQLBase):
    implements(IProcessorFamily)
    _table = 'ProcessorFamily'

    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)

    processors = SQLMultipleJoin('Processor', joinColumn='family')
    restricted = Bool(allow_none=False, default=False)

    def addProcessor(self, name, title, description):
        """See `IProcessorFamily`."""
        return Processor(family=self, name=name, title=title,
            description=description)

    def __repr__(self):
        return "<ProcessorFamily %r>" % self.title


class ProcessorFamilySet:
    implements(IProcessorFamilySet)

    def getByName(self, name):
        """Please see `IProcessorFamilySet`."""
        # Please note that ProcessorFamily.name is unique i.e. the database
        # will return a result set that's either empty or contains just one
        # ProcessorFamily row.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        rset = store.find(ProcessorFamily, ProcessorFamily.name == name)
        return rset.one()

    def getRestricted(self):
        """See `IProcessorFamilySet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(ProcessorFamily, ProcessorFamily.restricted == True)

    def getByProcessorName(self, name):
        """Please see `IProcessorFamilySet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        rset = store.find(
            ProcessorFamily,
            Processor.name == name, Processor.family == ProcessorFamily.id)
        # Each `Processor` is associated with exactly one `ProcessorFamily`
        # but there is also the possibility that the user specified a name for
        # a non-existent processor.
        return rset.one()

    def new(self, name, title, description, restricted=False):
        """See `IProcessorFamily`."""
        return ProcessorFamily(name=name, title=title,
            description=description, restricted=restricted)
