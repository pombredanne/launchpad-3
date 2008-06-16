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
from canonical.database.sqlbase import (
    SQLBase, sqlvalues)

from canonical.launchpad.interfaces.archive import (
    ArchivePurpose, IArchiveSet)
from canonical.launchpad.interfaces.archiverebuild import (
    ArchiveRebuildAlreadyExists, ArchiveRebuildStatus, IArchiveRebuild,
    IArchiveRebuildSet)


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
        dbName='status', notNull=True, schema=ArchiveRebuildStatus)

    reason = StringCol(
        dbName='reason', notNull=True)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    @property
    def title(self):
        return '%s for %s' % (
            self.archive.name, self.distroseries.displayname)


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
        # XXX cprov 20080612: implicitly prepending the distroseries
        # name to the archive name is quite evil. However it allow
        # us to publish rebuild archive for a given distribution
        # in a single disk location.
        archive_name = '%s-%s' % (distroseries.name, name)
        candidate = self.getByDistributionAndArchiveName(
            distroseries.distribution, archive_name)
        if candidate is not None:
            raise ArchiveRebuildAlreadyExists(
                "There is already an archive rebuild named '%s' in "
                "%s context. Choose another name."
                % (archive_name, distroseries.distribution.name))

        archive = getUtility(IArchiveSet).new(
            name=archive_name, distribution=distroseries.distribution,
            owner=registrant, purpose=ArchivePurpose.REBUILD)

        return ArchiveRebuild(
            archive=archive, distroseries=distroseries, reason=reason,
            registrant=registrant, status=ArchiveRebuildStatus.INPROGRESS)

    def getByDistroSeries(self, distroseries):
        """See `IArchiveRebuildSet`."""
        return ArchiveRebuild.selectBy(
            distroseries=distroseries, orderBy=['status', '-id'])
