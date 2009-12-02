# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []


from storm.locals import Int, Reference

from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol

from lp.soyuz.interfaces.sourcepackagebuild import ISourcePackageBuild


class SourcePackageBuild:

    implements(ISourcePackageBuild)
    __storm_table__ = 'Build'

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    processor = ForeignKey(dbName='processor', foreignKey='Processor',
        notNull=True)
    distroarchseries = ForeignKey(dbName='distroarchseries',
        foreignKey='DistroArchSeries', notNull=True)
    buildstate = EnumCol(dbName='buildstate', notNull=True,
                         schema=BuildStatus)
    sourcepackagerelease = ForeignKey(dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease', notNull=True)
    datebuilt = UtcDateTimeCol(dbName='datebuilt', default=None)
    buildduration = IntervalCol(dbName='buildduration', default=None)
    buildlog = ForeignKey(dbName='buildlog', foreignKey='LibraryFileAlias',
        default=None)
    builder = ForeignKey(dbName='builder', foreignKey='Builder',
        default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     notNull=True)
    dependencies = StringCol(dbName='dependencies', default=None)
    archive = ForeignKey(foreignKey='Archive', dbName='archive', notNull=True)

    date_first_dispatched = UtcDateTimeCol(dbName='date_first_dispatched')

    upload_log = ForeignKey(
        dbName='upload_log', foreignKey='LibraryFileAlias', default=None)
    
