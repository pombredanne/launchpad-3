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
from canonical.launchpad.interfaces.build import IBuild, IBuilder

#
# Build related SQLObjects
#

class SoyuzBuild(SQLBase):
    implements(IBuild)
    _table = 'Build'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        ForeignKey(name='processor', dbName='processor',
                   foreignKey='SoyuzProcessor', notNull=True),
        ForeignKey(name='distroarchrelease', dbName='distroarchrelease', 
                   foreignKey='SoyuzDistroArchRelease', notNull=True),
        IntCol('buildstate', dbName='buildstate', notNull=True),
        DateTimeCol('datebuilt', dbName='datebuilt'),
        DateTimeCol('buildduration', dbName='buildduration'),
        ForeignKey(name='buildlog', dbName='buildlog',
                   foreignKey='LibraryFileAlias'),
        ForeignKey(name='builder', dbName='builder',
                   foreignKey='SoyuzBuilder'),
        ForeignKey(name='gpgsigningkey', dbName='gpgsigningkey',
                   foreignKey='GPGKey'),
        StringCol('changes', dbName='changes'),
        ForeignKey(name='sourcepackagerelease', dbName='sourcepackagerelease',
                   foreignKey='SourcePackageRelease', notNull=True),

    ]



class SoyuzBuilder(SQLBase):
    implements(IBuilder)

    _table = 'Builder'
    _columns = [
        ForeignKey(name='processor', dbName='processor',
                   foreignKey='SoyuzProcessor', notNull=True),
        StringCol('fqdn', dbName='fqdn'),
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

