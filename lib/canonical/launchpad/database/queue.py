# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, IntCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase

# canonical imports
from canonical.launchpad.interfaces import IDistroReleaseQueue, \
                                           IDistroReleaseQueueBuild, \
                                           IDistroReleaseQueueSource

class DistroReleaseQueue(SQLBase):
    """A Queue item for Lucille"""
    implements(IDistroReleaseQueue)

    status = IntCol(dbName='status', unique=False, default=None, notNull=True)

    distrorelease = ForeignKey(dbName="distrorelease",
                               foreignKey='DistroRelease')

    # Join this table to the DistroReleaseQueueBuild and the
    # DistroReleaseQueueSource objects which are related.
    sources = MultipleJoin('DistroReleaseQueueSource',
                           joinColumn='distroreleasequeue')
    builds = MultipleJoin('DistroReleaseQueueBuild',
                          joinColumn='distroreleasequeue')

class DistroReleaseQueueBuild(SQLBase):
    """A Queue item's related builds (for Lucille)"""
    implements(IDistroReleaseQueueBuild)
    
    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
            )

    build = ForeignKey(
        dbName='build',
        foreignKey='Build'
            )

class DistroReleaseQueueSource(SQLBase):
    """A Queue item's related sourcepackagereleases (for Lucille)"""
    implements(IDistroReleaseQueueSource)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
            )

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease'
            )

    
