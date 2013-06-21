# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['ArchiveArch', 'ArchiveArchSet']

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


class ArchiveArchSet:
    """See `IArchiveArchSet`."""
    implements(IArchiveArchSet)

    def new(self, archive, processorfamily):
        """See `IArchiveArchSet`."""
        archivearch = ArchiveArch()
        archivearch.archive = archive
        archivearch.processorfamily = processorfamily
        IStore(ArchiveArch).add(archivearch)
        return archivearch

    def getByArchive(self, archive, processorfamily=None):
        """See `IArchiveArchSet`."""
        base_clauses = (ArchiveArch.archive == archive,)
        if processorfamily is not None:
            optional_clauses = (
                ArchiveArch.processorfamily == processorfamily,)
        else:
            optional_clauses = ()

        return IStore(ArchiveArch).find(
            ArchiveArch, *(base_clauses + optional_clauses)).order_by(
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
