
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
from canonical.launchpad.database import Product, Project
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistributionRole, IDistroReleaseRole, \
                                           IDistribution, IDistroRelease

from canonical.launchpad.database import Archive, Branch, ArchNamespace
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.binarypackage import BinaryPackage
from canonical.launchpad.database.person import Person

class DistributionRole(SQLBase):

    implements(IDistributionRole)

    _table = 'DistributionRole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='Person',
                   notNull=True),
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='Distribution', notNull=True),
        IntCol('role', dbName='role')
        ]

    def _rolename(self):
        for role in dbschema.DistributionRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role
    
    rolename = property(_rolename)
        

class DistroReleaseRole(SQLBase):

    implements(IDistroReleaseRole)

    _table = 'DistroReleaseRole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='Person',
                   notNull=True),
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='DistroRelease',
                   notNull=True),
        IntCol('role', dbName='role')
        ]

    def _rolename(self):
        # XXX: Daniel Debonzi 2004-10-14
        # using DistributionRole dbschema instead of DistroReleaseRole
        for role in dbschema.DistributionRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role

    rolename = property(_rolename)


class Distribution(SQLBase):

    implements(IDistribution)

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        StringCol('domainname', dbName='domainname'),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                   notNull=True)
        ]




class DistroArchRelease(SQLBase):
    """A release of an architecture on a particular distro."""

    _table = 'Distroarchrelease'

    _columns = [
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='DistroRelease', notNull=True),
        ForeignKey(name='processorfamily', dbName='processorfamily',
                   foreignKey='ProcessorFamily', notNull=True),
        StringCol('architecturetag', dbName='architecturetag', notNull=True),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person', 
                   notNull=True),
    ]

class Component(SQLBase):
    """  Component table SQLObject """

    _table = 'Component'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

class Section(SQLBase):
    """  Section table SQLObject """

    _table = 'Section'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

class DistroRelease(SQLBase):
    """Distrorelease SQLObject"""
    implements(IDistroRelease)

    _table = 'Distrorelease'
    _columns = [
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='Distribution', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        StringCol('version', dbName='version', notNull=True),
        ForeignKey(name='components', dbName='components', foreignKey='Schema',
                   notNull=True),
        ForeignKey(name='sections', dbName='sections', foreignKey='Schema',
                   notNull=True),
        IntCol('releasestate', dbName='releasestate', notNull=True),
        DateTimeCol('datereleased', dbName='datereleased', notNull=True),
        ForeignKey(name='parentrelease', dbName='parentrelease',
                   foreignKey='DistroRelease', notNull=False),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                   notNull=True),
        StringCol('lucilleconfig', dbName='lucilleconfig', notNull=False)
    ]

    def displayname(self):
        return "%s %s (%s)" % (self.distribution.title, self.version,
                               self.title)

    displayname = property(displayname)

    def parent(self):
        if self.parentrelease:
            return self.parentrelease.title
        return ''

    parent = property(parent)

    def _getState(self, value):
        for status in dbschema.DistributionReleaseState.items:
            if status.value == value:
                return status.title
        return 'Unknown'

    def state(self):
        return self._getState(self.releasestate)

    state = property(state)

    def sourcecount(self):
        q =  """SELECT COUNT (DISTINCT sourcepackagename.name)
                FROM sourcepackagename, SourcePackage,
                SourcePackageRelease, SourcePackagePublishing
                WHERE sourcepackagename.id = sourcepackage.sourcepackagename
                AND SourcePackagePublishing.sourcepackagerelease=
                                                  SourcePackageRelease.id
                AND SourcePackageRelease.sourcepackage = SourcePackage.id
                AND SourcePackagePublishing.distrorelease = %s;""" % (self.id)

        db = SourcePackage._connection._connection
        db_cursor = db.cursor()
        db_cursor.execute(q)        
        return db_cursor.fetchall()[0][0]

    sourcecount = property(sourcecount)

    def binarycount(self):
        q = """SELECT COUNT (DISTINCT binarypackagename.name) FROM
               binarypackagename, packagepublishing, binarypackage,
               distroarchrelease WHERE PackagePublishing.binarypackage =
               BinaryPackage.id AND PackagePublishing.distroarchrelease =
               DistroArchRelease.id AND DistroArchRelease.distrorelease = %s
               AND binarypackagename.id = binarypackage.binarypackagename;
               """ % (self.id)

        db = BinaryPackage._connection._connection
        db_cursor = db.cursor()
        db_cursor.execute(q)
        return db_cursor.fetchall()[0][0]
                
    binarycount = property(binarycount)


