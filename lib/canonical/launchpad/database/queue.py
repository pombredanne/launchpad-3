# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroReleaseQueue', 'DistroReleaseQueueBuild',
           'DistroReleaseQueueSource', 'DistroReleaseQueueCustom']

from zope.interface import implements

from sqlobject import ForeignKey, MultipleJoin

from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import (
    EnumCol, DistroReleaseQueueStatus, DistroReleaseQueueCustomFormat,
    PackagePublishingPocket)

from canonical.launchpad.interfaces import (
    IDistroReleaseQueue, IDistroReleaseQueueBuild, IDistroReleaseQueueSource,
    IDistroReleaseQueueCustom)


class DistroReleaseQueue(SQLBase):
    """A Queue item for Lucille."""
    implements(IDistroReleaseQueue)

    status = EnumCol(dbName='status', unique=False, default=None, notNull=True,
                     schema=DistroReleaseQueueStatus)

    distrorelease = ForeignKey(dbName="distrorelease",
                               foreignKey='DistroRelease')

    pocket = EnumCol(dbName='pocket', unique=False, default=None, notNull=True,
                     schema=PackagePublishingPocket)


    # Join this table to the DistroReleaseQueueBuild and the
    # DistroReleaseQueueSource objects which are related.
    sources = MultipleJoin('DistroReleaseQueueSource',
                           joinColumn='distroreleasequeue')
    builds = MultipleJoin('DistroReleaseQueueBuild',
                          joinColumn='distroreleasequeue')
    # Also the custom files associated with the build.
    customfiles = MultipleJoin('DistroReleaseQueueCustom',
                               joinColumn='distroreleasequeue')

class DistroReleaseQueueBuild(SQLBase):
    """A Queue item's related builds (for Lucille)."""
    implements(IDistroReleaseQueueBuild)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    build = ForeignKey(dbName='build', foreignKey='Build')


class DistroReleaseQueueSource(SQLBase):
    """A Queue item's related sourcepackagereleases (for Lucille)."""
    implements(IDistroReleaseQueueSource)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease'
        )

    
class DistroReleaseQueueCustom(SQLBase):
    """A Queue item's related custom format uploads."""
    implements(IDistroReleaseQueueCustom)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    customformat = EnumCol(dbName='customformat', unique=False,
                           default=None, notNull=True,
                           schema=DistroReleaseQueueCustomFormat)

    libraryfilealias = ForeignKey(dbName='libraryfilealias',
                                  foreignKey="LibraryFileAlias",
                                  notNull=True)
    
