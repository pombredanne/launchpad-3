# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'ArchiveArch',
    'ArchiveArchSet'
    ]

from storm.expr import (
    And,
    LeftJoin,
    )
from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.interface import implements

from lp.services.database.interfaces import IStore
from lp.soyuz.interfaces.archivearch import (
    IArchiveArch,
    IArchiveArchSet,
    )
from lp.soyuz.model.processor import ProcessorFamily


class ArchiveArch(Storm):
    """See `IArchiveArch`."""
    implements(IArchiveArch)
    __storm_table__ = 'ArchiveArch'
    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')
    processorfamily_id = Int(name='processorfamily', allow_none=True)
    processorfamily = Reference(processorfamily_id, 'ProcessorFamily.id')
    processor_id = Int(name='processor', allow_none=True)
    processor = Reference(processor_id, 'Processor.id')


class ArchiveArchSet:
    """See `IArchiveArchSet`."""
    implements(IArchiveArchSet)

    def new(self, archive, processorfamily):
        """See `IArchiveArchSet`."""
        processor = processorfamily.processors[0]
        archivearch = ArchiveArch()
        archivearch.archive = archive
        archivearch.processorfamily = processorfamily
        archivearch.processor = processor
        IStore(ArchiveArch).add(archivearch)
        return archivearch

    def getByArchive(self, archive, processor=None):
        """See `IArchiveArchSet`."""
        clauses = [ArchiveArch.archive == archive]
        if processor is not None:
            clauses.append(ArchiveArch.processor_id == processor.id)

        return IStore(ArchiveArch).find(ArchiveArch, *clauses).order_by(
            ArchiveArch.id)

    def getRestrictedFamilies(self, archive):
        """See `IArchiveArchSet`."""
        origin = (
            ProcessorFamily,
            LeftJoin(
                ArchiveArch,
                And(ArchiveArch.archive == archive.id,
                    ArchiveArch.processorfamily == ProcessorFamily.id)))
        return IStore(ArchiveArch).using(*origin).find(
            (ProcessorFamily, ArchiveArch),
            ProcessorFamily.restricted == True).order_by(ProcessorFamily.name)
