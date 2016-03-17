# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A file in an archive."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ArchiveFile',
    'ArchiveFileSet',
    ]

import os.path

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.soyuz.interfaces.archivefile import (
    IArchiveFile,
    IArchiveFileSet,
    )


@implementer(IArchiveFile)
class ArchiveFile(Storm):
    """See `IArchiveFile`."""

    __storm_table__ = 'ArchiveFile'

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    container = Unicode(name='container', allow_none=False)

    path = Unicode(name='path', allow_none=False)

    library_file_id = Int(name='library_file', allow_none=False)
    library_file = Reference(library_file_id, 'LibraryFileAlias.id')

    scheduled_deletion_date = DateTime(
        name='scheduled_deletion_date', tzinfo=pytz.UTC, allow_none=True)

    def __init__(self, archive, container, path, library_file):
        """Construct an `ArchiveFile`."""
        super(ArchiveFile, self).__init__()
        self.archive = archive
        self.container = container
        self.path = path
        self.library_file = library_file
        self.scheduled_deletion_date = None


@implementer(IArchiveFileSet)
class ArchiveFileSet:
    """See `IArchiveFileSet`."""

    @staticmethod
    def new(archive, container, path, library_file):
        """See `IArchiveFileSet`."""
        archive_file = ArchiveFile(archive, container, path, library_file)
        IMasterStore(ArchiveFile).add(archive_file)
        return archive_file

    @classmethod
    def newFromFile(cls, archive, container, root, path, size, content_type):
        with open(os.path.join(root, path), "rb") as f:
            library_file = getUtility(ILibraryFileAliasSet).create(
                os.path.basename(path), size, f, content_type,
                restricted=archive.private)
        return cls.new(archive, container, path, library_file)

    @staticmethod
    def getByArchive(archive, container=None, eager_load=False):
        """See `IArchiveFileSet`."""
        clauses = [ArchiveFile.archive == archive]
        # XXX cjwatson 2016-03-15: We'll need some more sophisticated way to
        # match containers once we're using them for custom uploads.
        if container is not None:
            clauses.append(ArchiveFile.container == container)
        archive_files = IStore(ArchiveFile).find(ArchiveFile, *clauses)

        def eager_load(rows):
            lfas = load_related(LibraryFileAlias, rows, ["library_file_id"])
            load_related(LibraryFileContent, lfas, ["contentID"])

        if eager_load:
            return DecoratedResultSet(archive_files, pre_iter_hook=eager_load)
        else:
            return archive_files

    @staticmethod
    def scheduleDeletion(archive_files, stay_of_execution):
        """See `IArchiveFileSet`."""
        archive_file_ids = set(
            archive_file.id for archive_file in archive_files)
        rows = IMasterStore(ArchiveFile).find(
            ArchiveFile, ArchiveFile.id.is_in(archive_file_ids))
        rows.set(scheduled_deletion_date=UTC_NOW + stay_of_execution)

    @staticmethod
    def getContainersToReap(archive, container_prefix=None):
        clauses = [
            ArchiveFile.archive == archive,
            ArchiveFile.scheduled_deletion_date < UTC_NOW,
            ]
        if container_prefix is not None:
            clauses.append(ArchiveFile.container.startswith(container_prefix))
        return IStore(ArchiveFile).find(
            ArchiveFile.container, *clauses).group_by(ArchiveFile.container)

    @staticmethod
    def reap(archive, container=None):
        """See `IArchiveFileSet`."""
        clauses = [
            ArchiveFile.archive == archive,
            ArchiveFile.scheduled_deletion_date < UTC_NOW,
            ]
        if container is not None:
            clauses.append(ArchiveFile.container == container)
        IMasterStore(ArchiveFile).find(ArchiveFile, *clauses).remove()
