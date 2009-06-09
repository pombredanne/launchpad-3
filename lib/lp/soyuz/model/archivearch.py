# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ArchiveArch', 'ArchiveArchSet']

from zope.component import getUtility
from zope.interface import implements

from lp.soyuz.interfaces.archivearch import (
    IArchiveArch, IArchiveArchSet)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

from storm.locals import Int, Reference, Storm


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
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        archivearch = ArchiveArch()
        archivearch.archive = archive
        archivearch.processorfamily = processorfamily
        store.add(archivearch)
        return archivearch

    def getByArchive(self, archive, processorfamily=None):
        """See `IArchiveArchSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        base_clauses = (ArchiveArch.archive == archive,)
        if processorfamily is not None:
            optional_clauses = (
                ArchiveArch.processorfamily == processorfamily,)
        else:
            optional_clauses = ()
        return store.find(
            ArchiveArch, *(base_clauses + optional_clauses))
