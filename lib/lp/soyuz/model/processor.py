# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['Processor', 'ProcessorFamily', 'ProcessorFamilySet']

from sqlobject import (
    ForeignKey,
    SQLMultipleJoin,
    StringCol,
    )
from storm.locals import Bool
from zope.interface import implements

from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase
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
        processor = IStore(Processor).find(
            Processor, Processor.name == name).one()
        if processor is None:
            raise ProcessorNotFound(name)
        return processor

    def getAll(self):
        """See `IProcessorSet`."""
        return IStore(Processor).find(Processor)


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
        return IStore(ProcessorFamily).find(
            ProcessorFamily, ProcessorFamily.name == name).one()

    def getRestricted(self):
        """See `IProcessorFamilySet`."""
        return IStore(ProcessorFamily).find(
            ProcessorFamily, ProcessorFamily.restricted == True)

    def getByProcessorName(self, name):
        """Please see `IProcessorFamilySet`."""
        # Each `Processor` is associated with exactly one `ProcessorFamily`
        # but there is also the possibility that the user specified a name for
        # a non-existent processor.
        return IStore(ProcessorFamily).find(
            ProcessorFamily,
            Processor.name == name,
            Processor.family == ProcessorFamily.id).one()

    def new(self, name, title, description, restricted=False):
        """See `IProcessorFamily`."""
        return ProcessorFamily(name=name, title=title,
            description=description, restricted=restricted)
