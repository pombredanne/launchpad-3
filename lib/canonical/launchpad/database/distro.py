
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
from canonical.launchpad.database import SourcePackageBugAssignment
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistributionRole
from canonical.launchpad.interfaces import IDistroReleaseRole
from canonical.launchpad.interfaces import IDistribution
from canonical.launchpad.interfaces import IDistroRelease
from canonical.launchpad.interfaces import IDistrosSet
from canonical.launchpad.interfaces import IDistroTools

from canonical.launchpad.database import Archive, Branch, ArchNamespace
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.sourcepackage import SourcePackageInDistro
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
        for role in dbschema.DistroReleaseRole.items:
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

    releases = MultipleJoin('DistroRelease', 
                            joinColumn='distribution') 
    role_users = MultipleJoin('DistributionRole', 
                              joinColumn='distribution')
   
    def getRelease(self, name):
        return DistroRelease.selectBy(distributionID = self.id,
                                      name=name)[0]

    def bugCounter(self):
        counts = []

        clauseTables = ("VSourcePackageInDistro",
                        "SourcePackage")
        severities = [
            dbschema.BugAssignmentStatus.NEW,
            dbschema.BugAssignmentStatus.ACCEPTED,
            dbschema.BugAssignmentStatus.REJECTED,
            dbschema.BugAssignmentStatus.FIXED]

        query = ("sourcepackagebugassignment.sourcepackage = sourcepackage.id AND "
                 "sourcepackage.sourcepackagename = vsourcepackageindistro.sourcepackagename AND "
                 "vsourcepackageindistro.distro = %s AND "
                 "sourcepackagebugassignment.bugstatus = %i")

        for severity in severities:
            query = query %(quote(self.id), severity)
            count = SourcePackageBugAssignment.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        return counts

    bugCounter = property(bugCounter)

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

    architectures = MultipleJoin( 'DistroArchRelease',
                                  joinColumn='distrorelease' )
    role_users = MultipleJoin('DistroReleaseRole', 
                              joinColumn='distrorelease')

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

    def bugCounter(self):
        counts = []
        
        clauseTables = ("VSourcePackageInDistro",
                        "SourcePackage")
        severities = [
            dbschema.BugAssignmentStatus.NEW,
            dbschema.BugAssignmentStatus.ACCEPTED,
            dbschema.BugAssignmentStatus.FIXED,
            dbschema.BugAssignmentStatus.REJECTED
        ]
        
        _query = ("sourcepackagebugassignment.sourcepackage = sourcepackage.id AND "
                 "sourcepackage.sourcepackagename = vsourcepackageindistro.sourcepackagename AND "
                 "vsourcepackageindistro.distrorelease = %i AND "
                 "sourcepackagebugassignment.bugstatus = %i"
                 )

        for severity in severities:
            query = _query %(self.id, int(severity))
            count = SourcePackageBugAssignment.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        counts.insert(0, sum(counts))
        return counts

    bugCounter = property(bugCounter)

       

    def getBugSourcePackages(self):
        """Get SourcePackages in a DistroRelease with BugAssignement"""

        clauseTables=["SourcePackageBugAssignment",]
        query = ("VSourcePackageInDistro.distrorelease = %i AND "
                 "VSourcePackageInDistro.id = SourcePackageBugAssignment.sourcepackage AND "
                 "(SourcePackageBugAssignment.bugstatus != %i OR "
                 "SourcePackageBugAssignment.bugstatus != %i)"
                 %(self.id,
                   int(dbschema.BugAssignmentStatus.FIXED),
                   int(dbschema.BugAssignmentStatus.REJECTED)))

        return SourcePackageInDistro.select(query, clauseTables=clauseTables)



class DistrosSet(object):
    """This class is to deal with Distribution related stuff"""

    implements(IDistrosSet)

    def getDistros(self):
        """Returns all Distributions available on the datasbase"""
        return Distribution.select()

    def getDistrosCounter(self):
        """Returns the number of Distributions available"""
        return Distribution.select().count()

    def getDistribution(self, name):
        """Returns a Distribution with name = name"""
        return Distribution.selectBy(name=name)[0]

class DistroTools(object):
    """Tools for help Distribution and DistroRelase Manipulation """

    implements(IDistroTools)

    def createDistro(self, owner, title, description, domain):
        """Create a Distribution """
        ##XXX: cprov 20041207
        ## Verify the name constraint as the postgresql does.
        ## What about domain ???        
        name = title.lower()
        
        distro = Distribution(name=name,
                              title=title,
                              description=description,
                              domainname=domain,
                              owner=owner)

        self.createDistributionRole(distro.id, owner,
                                    dbschema.DistributionRole.DM.value)

        return distro
        

    def createDistroRelease(self, owner, title, distribution, shortdesc,
                            description, version, parent):
        ##XXX: cprov 20041207
        ## Verify the name constraint as the postgresql does.
        name = title.lower()

        ## XXX: cprov 20041207
        ## Define missed fields

        release = DistroRelease(name=name,
                                distribution=distribution,
                                title=title,
                                shortdesc=shortdesc,
                                description=description,
                                version=version,
                                owner=owner,
                                parentrelease=int(parent),
                                datereleased=datetime.utcnow(),
                                components=1,
                                releasestate=1,
                                sections=1,
                                lucilleconfig='')

        self.createDistroReleaseRole(release.id, owner,
                                     dbschema.DistroReleaseRole.RM.value)

        return release
    
    def getDistroReleases(self):
        return DistroRelease.select()
    

    def createDistributionRole(self, container_id, person, role):
        return DistributionRole(distribution=container_id,
                                personID=person, role=role)

    def createDistroReleaseRole(self, container_id, person, role):
        return DistroReleaseRole(distrorelease=container_id,
                                 personID=person, role=role)

