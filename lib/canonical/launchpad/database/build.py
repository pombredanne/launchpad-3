# Python imports
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, DateTimeCol, BoolCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import IBuild, IBuilder, IBuildSet, \
                                           IBuildQueue
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import BuildStatus

#
#
#

class Build(SQLBase):
    implements(IBuild)
    _table = 'Build'

    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=True,
                                 default=UTC_NOW)
    processor = ForeignKey(dbName='processor', foreignKey='Processor', 
                           notNull=True)
    distroarchrelease = ForeignKey(dbName='distroarchrelease', 
                                   foreignKey='DistroArchRelease', 
                                   notNull=True)
    buildstate = EnumCol(dbName='buildstate', notNull=True,
                         schema=BuildStatus)
    datebuilt = UtcDateTimeCol(dbName='datebuilt')
    buildduration = DateTimeCol(dbName='buildduration')
    buildlog = ForeignKey(dbName='buildlog', foreignKey='LibraryFileAlias')
    builder = ForeignKey(dbName='builder', foreignKey='Builder')
    gpgsigningkey = ForeignKey(dbName='gpgsigningkey', foreignKey='GPGKey')
    changes = StringCol(dbName='changes')
    sourcepackagerelease = ForeignKey(dbName='sourcepackagerelease',
                                      foreignKey='SourcePackageRelease', 
                                      notNull=True)

class BuildSet(object):
    implements(IBuildSet)
    
    def getBuildBySRAndArchtag(self, sourcepackagereleaseID, archtag):
        clauseTables = ('DistroArchRelease', )
        query = ('Build.sourcepackagerelease = %i '
                 'AND Build.distroarchrelease = DistroArchRelease.id '
                 'AND DistroArchRelease.architecturetag = %s'
                 % (sourcepackagereleaseID, quote(archtag))
                 )

        return Build.select(query, clauseTables=clauseTables)


class Builder(SQLBase):
    implements(IBuilder)
    _table = 'Builder'

    processor = ForeignKey(dbName='processor', foreignKey='Processor', 
                           notNull=True)
    fqdn = StringCol(dbName='fqdn')
    name = StringCol(dbName='name')
    title = StringCol(dbName='title')
    description = StringCol(dbName='description')
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes')
    
class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"

    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    builder = ForeignKey(dbName='builder', foreignKey='Builder',
                         notNull=False)
    created = UtcDateTimeCol(dbName='created', notNull=True)
    buildstart = UtcDateTimeCol(dbName='buildstart', notNull=False)
    logtail = StringCol(dbName='logtail', notNull=False)

