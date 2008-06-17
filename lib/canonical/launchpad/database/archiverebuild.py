# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ArchiveRebuild',
    'ArchiveRebuildSet',
    ]


from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, IArchiveSet)
from canonical.launchpad.interfaces.archiverebuild import (
    ArchiveRebuildAlreadyExists, ArchiveRebuildInconsistentStateError,
    ArchiveRebuildStatus, ArchiveRebuildStatusWriteProtectedError,
    IArchiveRebuild, IArchiveRebuildSet)


# XXX cprov 20080617: code copied from database/queue.py. Idealy it could be
# shared, the only difference is the exception raised on write-portected
# errors.

class PassthroughStatusValue:
    """A wrapper to allow setting ArchiveRebuild.status."""

    def __init__(self, value):
        self.value = value


def validate_status(self, attr, value):
    # Is the status wrapped in the special passthrough class?
    if isinstance(value, PassthroughStatusValue):
        return value.value

    raise ArchiveRebuildStatusWriteProtectedError(
        'Directly write on archive rebuild status is forbidden use the '
        'provided methods to set it.')


class ArchiveRebuild(SQLBase):
    """See `IArchiveRebuild`."""

    implements(IArchiveRebuild)

    _defaultOrder = ['id']

    archive = ForeignKey(
        dbName='archive', foreignKey='Archive', notNull=True)

    distroseries = ForeignKey(
        dbName="distroseries", foreignKey='DistroSeries', notNull=True)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)

    status = EnumCol(
        dbName='status', notNull=True, schema=ArchiveRebuildStatus,
        default=ArchiveRebuildStatus.INPROGRESS,
        storm_validator=validate_status)

    reason = StringCol(
        dbName='reason', notNull=True)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    @property
    def title(self):
        """See `IArchiveRebuild`."""
        return '%s for %s' % (
            self.archive.name, self.distroseries.displayname)

    def _setStatus(self, target_status):
        """Protected status setter.

        :param target_status: `ArchiveRebuildStatus` to be set.

        :raise `ArchiveRebuildInsistentStatusError` if the given status
            is already set.
        """
        if self.status == target_status:
            raise ArchiveRebuildInconsistentStateError(
                "Archive rebuild is already in %s status"
                % target_status.name)
        self.status = PassthroughStatusValue(target_status)

    def setInProgress(self):
        """See `IArchiveRebuild`."""
        self._setStatus(ArchiveRebuildStatus.INPROGRESS)

    def setCancelled(self):
        """See `IArchiveRebuild`."""
        self._setStatus(ArchiveRebuildStatus.CANCELLED)

    def setComplete(self):
        """See `IArchiveRebuild`."""
        self._setStatus(ArchiveRebuildStatus.COMPLETE)

    def setObsolete(self):
        """See `IArchiveRebuild`."""
        self._setStatus(ArchiveRebuildStatus.OBSOLETE)


class ArchiveRebuildSet:
    """See `IArchiveRebuildSet`."""

    implements(IArchiveRebuildSet)

    def __iter__(self):
        """See `IArchiveRebuildSet`."""
        return iter(ArchiveRebuild.select(orderBy=['-id']))

    def get(self, rebuild_id):
        """See `IArchiveRebuildSet`."""
        return ArchiveRebuild.get(rebuild_id)

    def getByDistributionAndArchiveName(self, distribution, archive_name):
        """See `IArchiveRebuildSet`."""
        query = """
            ArchiveRebuild.archive = Archive.id AND
            Archive.distribution = %s AND
            Archive.name = %s
        """ % sqlvalues(distribution, archive_name)

        return ArchiveRebuild.selectOne(query, clauseTables=['Archive'])

    def new(self, name, distroseries, registrant, reason):
        """See `IArchiveRebuildSet`."""
        # Implicitly prepending the distroseries name to the archive
        # name is quite evil. However it allows us to publish rebuild
        # archives for a given distribution in a single disk location.
        archive_name = '%s-%s' % (distroseries.name, name)
        candidate = self.getByDistributionAndArchiveName(
            distroseries.distribution, archive_name)
        if candidate is not None:
            raise ArchiveRebuildAlreadyExists(
                "An archive rebuild named '%s' for '%s' in '%s' "
                "already exists." % (name, distroseries.name,
                                     distroseries.distribution.name))

        archive = getUtility(IArchiveSet).new(
            name=archive_name, distribution=distroseries.distribution,
            owner=registrant, purpose=ArchivePurpose.REBUILD)

        return ArchiveRebuild(
            archive=archive, distroseries=distroseries, reason=reason,
            registrant=registrant)

    def getByDistroSeries(self, distroseries):
        """See `IArchiveRebuildSet`."""
        return ArchiveRebuild.selectBy(
            distroseries=distroseries, orderBy=['status', '-id'])
