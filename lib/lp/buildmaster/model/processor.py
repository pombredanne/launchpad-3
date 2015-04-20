# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'Processor',
    'ProcessorSet',
    ]

from sqlobject import StringCol
from storm.locals import Bool
from zope.interface import implements

from lp.buildmaster.interfaces.processor import (
    IProcessor,
    IProcessorSet,
    ProcessorNotFound,
    )
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase


class Processor(SQLBase):
    implements(IProcessor)
    _table = 'Processor'

    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    restricted = Bool(allow_none=False, default=False)
    build_by_default = Bool(allow_none=False, default=False)
    supports_virtualized = Bool(allow_none=False, default=False)
    supports_nonvirtualized = Bool(allow_none=False, default=True)

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

    def getRestricted(self):
        """See `IProcessorSet`."""
        return IStore(Processor).find(Processor, Processor.restricted == True)

    def new(self, name, title, description, restricted=False,
            build_by_default=False, supports_virtualized=False,
            supports_nonvirtualized=True):
        """See `IProcessorSet`."""
        return Processor(
            name=name, title=title, description=description,
            restricted=restricted, build_by_default=build_by_default,
            supports_virtualized=supports_virtualized,
            supports_nonvirtualized=supports_nonvirtualized)
