# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBuild, IBuilder, IBuildSet

#
# Build related SQLObjects
#

class Build(SQLBase):
    implements(IBuild)
    _table = 'Build'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        ForeignKey(name='processor', dbName='processor',
                   foreignKey='Processor', notNull=True),
        ForeignKey(name='distroarchrelease', dbName='distroarchrelease', 
                   foreignKey='DistroArchRelease', notNull=True),
        IntCol('buildstate', dbName='buildstate', notNull=True),
        DateTimeCol('datebuilt', dbName='datebuilt'),
        DateTimeCol('buildduration', dbName='buildduration'),
        ForeignKey(name='buildlog', dbName='buildlog',
                   foreignKey='LibraryFileAlias'),
        ForeignKey(name='builder', dbName='builder',
                   foreignKey='Builder'),
        ForeignKey(name='gpgsigningkey', dbName='gpgsigningkey',
                   foreignKey='GPGKey'),
        StringCol('changes', dbName='changes'),
        ForeignKey(name='sourcepackagerelease', dbName='sourcepackagerelease',
                   foreignKey='SourcePackageRelease', notNull=True),

    ]


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
    _columns = [
        ForeignKey(name='processor', dbName='processor',
                   foreignKey='Processor', notNull=True),
        StringCol('fqdn', dbName='fqdn'),
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

    
