
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
from canonical.launchpad.interfaces import ISourcePackageRelease, IManifestEntry, \
                                           IBranch, IChangeset, \
                                           ISourcePackage, ISoyuzPerson, \
                                           IBinaryPackage, \
                                           IDistributionRole, IDistroReleaseRole, \
                                           IDistribution, IRelease

from canonical.launchpad.database import Archive, Branch, ArchNamespace

#
#
#

class DistributionRole(SQLBase):

    implements(IDistributionRole)

    _table = 'Distributionrole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
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

    _table = 'Distroreleaserole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
                   notNull=True),
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='Release',
                   notNull=True),
        IntCol('role', dbName='role')
        ]

    def _rolename(self):
        # FIXME: using DistributionRole dbschema instead of DistroRelease
        for role in dbschema.DistributionRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role

    rolename = property(_rolename)


class Distribution(SQLBase):
    """An open source distribution."""

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', foreignKey='SoyuzPerson', dbName='owner', 
                   notNull=True),
    ]


class SoyuzDistroArchRelease(SQLBase):
    """A release of an architecture on a particular distro."""

    _table = 'DistroArchRelease'

    _columns = [
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='SoyuzDistroRelease', notNull=True),
        ForeignKey(name='processorfamily', dbName='processorfamily',
                   foreignKey='SoyuzProcessorFamily', notNull=True),
        StringCol('architecturetag', dbName='architecturetag', notNull=True),
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson', 
                   notNull=True),
    ]

class SoyuzComponent(SQLBase):
    """ Soyuz Component table SQLObject """

    _table = 'Component'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

class SoyuzSection(SQLBase):
    """ Soyuz Section table SQLObject """

    _table = 'Section'

    _columns = [
        StringCol('name', dbName='name', notNull=True),
        ]

class SoyuzPackagePublishing(SQLBase):

    _table = 'PackagePublishing'
    
    _columns = [
        ForeignKey(name='binaryPackage', foreignKey='SoyuzBinaryPackage', 
                   dbName='binarypackage', notNull=True),
        ForeignKey(name='distroArchrelease', dbName='distroArchrelease',
                   foreignKey='SoyuzDistroArchRelease', notNull=True),
        ForeignKey(name='component', dbName='component',
                   foreignKey='SoyuzComponent', notNull=True),
        ForeignKey(name='section', dbName='section', foreignKey='SoyuzSection',
                   notNull=True),
        IntCol('priority', dbName='priority', notNull=True),
    ]

class SoyuzBinaryPackage(SQLBase):
    implements(IBinaryPackage)
    _table = 'BinaryPackage'
    _columns = [
        ForeignKey(name='binarypackagename', dbName='binarypackagename', 
                   foreignKey='SoyuzBinaryPackageName', notNull=True),
        StringCol('version', dbName='version', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True, default=""),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='build', dbName='build', foreignKey='SoyuzBuild',
                   notNull=True),
        IntCol('binpackageformat', dbName='binpackageformat', notNull=True),
        ForeignKey(name='component', dbName='component',
                   foreignKey='SoyuzComponent', notNull=True),
        ForeignKey(name='section', dbName='section', foreignKey='SoyuzSection',
                   notNull=True),
        IntCol('priority', dbName='priority'),
        StringCol('shlibdeps', dbName='shlibdeps'),
        StringCol('depends', dbName='depends'),
        StringCol('recommends', dbName='recommends'),
        StringCol('suggests', dbName='suggests'),
        StringCol('conflicts', dbName='conflicts'),
        StringCol('replaces', dbName='replaces'),
        StringCol('provides', dbName='provides'),
        BoolCol('essential', dbName='essential'),
        IntCol('installedsize', dbName='installedsize'),
        StringCol('copyright', dbName='copyright'),
        StringCol('licence', dbName='licence'),
    ]

    # XXX: Why does Zope raise NotFound if name is a property?  A property would
    #      be more appropriate.
    #name = property(lambda self: self.binarypackagename.name)
    def name(self):
        return self.binarypackagename.name
    name = property(name)

    def maintainer(self):
        return self.sourcepackagerelease.sourcepackage.maintainer
    maintainer = property(maintainer)

    def current(self, distroRelease):
        """Currently published releases of this package for a given distro.
        
        :returns: iterable of SourcePackageReleases
        """
        return self.build.sourcepackagerelease.sourcepackage.current(distroRelease)

    def lastversions(self, distroRelease):
        last = list(SoyuzSourcePackageRelease.select(
            'SourcePackageUpload.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackageUpload.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackageUpload.uploadstatus = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id, self.build.sourcepackagerelease.sourcepackage.id,dbschema.SourceUploadStatus.SUPERCEDED)
        ))
        if last:
            return last
        else:
            return None

    def _priority(self):
        for priority in dbschema.BinaryPackagePriority.items:
            if priority.value == self.priority:
                return priority.title
        return 'Unknown (%d)' %self.priority

    pkgpriority = property(_priority)

class SoyuzBinaryPackageName(SQLBase):
    _table = 'BinaryPackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
    ]
        

class SoyuzBuild(SQLBase):
    _table = 'Build'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        ForeignKey(name='processor', dbName='Processor',
                   foreignKey='SoyuzProcessor', notNull=True),
        ForeignKey(name='distroarchrelease', dbName='distroarchrelease', 
                   foreignKey='SoyuzDistroArchRelease', notNull=True),
        IntCol('buildstate', dbName='buildstate', notNull=True),
        DateTimeCol('datebuilt', dbName='datebuilt'),
        DateTimeCol('buildduration', dbName='buildduration'),
        ForeignKey(name='buildlog', dbName='buildlog',
                   foreignKey='LibraryFileAlias'),
        ForeignKey(name='builder', dbName='builder',
                   foreignKey='Builder'),
        ForeignKey(name='gpgsigningkey', dbName='gpgsigningkey',
                   foreignKey='GPGKey'),
        ForeignKey(name='sourcepackagerelease', dbName='sourcepackagerelease',
                   foreignKey='SoyuzSourcePackageRelease', notNull=True),

    ]
 


class SoyuzSourcePackage(SQLBase):
    """A source package, e.g. apache2."""

    implements(ISourcePackage)

    _table = 'SourcePackage'
    _columns = [
        ForeignKey(name='maintainer', foreignKey='SoyuzPerson', dbName='maintainer',
                   notNull=True),
        ForeignKey(name='sourcepackagename', foreignKey='SoyuzSourcePackageName',
                   dbName='sourcepackagename', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='manifest', foreignKey='Manifest', dbName='manifest', 
                   default=None),
        ForeignKey(name='distro', foreignKey='Distribution', dbName='distro'),
    ]
    releases = MultipleJoin('SoyuzSourcePackageRelease',
                            joinColumn='sourcepackage')

    def name(self):
        return self.sourcepackagename.name
    name = property(name)

    def product(self):
        try:
            return Product.select(
                "Product.id = Packaging.product AND "
                "Packaging.sourcepackage = %d"
                % self.id
            )[0]
        except IndexError:
            # No corresponding product
            return None
    product = property(product)

    def getManifest(self):
        return self.manifest

    def getRelease(self, version):
        return SoyuzSourcePackageRelease.selectBy(version=version)[0]

    def uploadsByStatus(self, distroRelease, status):
        uploads = list(SoyuzSourcePackageRelease.select(
            'SourcePackageUpload.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackageUpload.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackageUpload.uploadstatus = %d'
            % (distroRelease.id, self.id, status)
        ))

        if uploads:
            return uploads[0]
        else:
            return None

    def proposed(self, distroRelease):
        return self.uploadsByStatus(distroRelease,
                                    dbschema.SourceUploadStatus.PROPOSED)

    def current(self, distroRelease):
        """Currently published releases of this package for a given distro.
        
        :returns: iterable of SourcePackageReleases
        """
        sourcepackagereleases = SoyuzSourcePackageRelease.select(
            'SourcePackageUpload.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackageUpload.distrorelease = %d'
            ' AND SourcepackageRelease.sourcepackage = %d'
            ' AND SourcePackageUpload.uploadstatus = %d'
            % (distroRelease.id, self.id, dbschema.SourceUploadStatus.PUBLISHED)
        )

        return sourcepackagereleases

    def lastversions(self, distroRelease):
        last = list(SoyuzSourcePackageRelease.select(
            'SourcePackageUpload.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackageUpload.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackageUpload.uploadstatus = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id, self.id,dbschema.SourceUploadStatus.SUPERCEDED)
        ))

        if last:
            return last
        else:
            return None

class SoyuzSourcePackageName(SQLBase):
    _table = 'SourcePackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
    ]


class SoyuzSourcePackageRelease(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(ISourcePackageRelease)

    _table = 'SourcePackageRelease'
    _columns = [
        ForeignKey(name='sourcepackage', foreignKey='SoyuzSourcePackage',
                   dbName='sourcepackage', notNull=True),
        IntCol('srcpackageformat', dbName='srcpackageformat', notNull=True),
        ForeignKey(name='creator', foreignKey='SoyuzPerson', dbName='creator'),
        StringCol('version', dbName='version'),
        DateTimeCol('dateuploaded', dbName='dateuploaded', notNull=True,
                    default='NOW'),
        IntCol('urgency', dbName='urgency', notNull=True),
        ForeignKey(name='component', foreignKey='SoyuzComponent', dbName='component'),
        StringCol('changelog', dbName='changelog'),
        StringCol('builddepends', dbName='builddepends'),
        StringCol('builddependsindep', dbName='builddependsindep'),
    ]

    builds = MultipleJoin('SoyuzBuild', joinColumn='sourcepackagerelease')

    def architecturesReleased(self, distroRelease):
        archReleases = Set(SoyuzDistroArchRelease.select(
            'PackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND PackagePublishing.binarypackage = BinaryPackage.id '
            'AND BinaryPackage.build = Build.id '
            'AND Build.sourcepackagerelease = %d'
            % (distroRelease.id, self.id)
        ))
        return archReleases

    def _urgency(self):
        for urgency in dbschema.SourcePackageUrgency.items:
            if urgency.value == self.urgency:
                return urgency.title
        return 'Unknown (%d)' %self.urgency

    def binaries(self):
        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i'
                 %self.id 
                 )

        return SoyuzBinaryPackage.select(query)
        
    binaries = property(binaries)

    pkgurgency = property(_urgency)


def getSourcePackage(name):
    return SourcePackage.selectBy(name=name)


def createSourcePackage(name, maintainer=0):
    # FIXME: maintainer=0 is a hack.  It should be required (or the DB shouldn't
    #        have NOT NULL on that column).
    return SourcePackage(
        name=name, 
        maintainer=maintainer,
        title='', # FIXME
        description='', # FIXME
    )

def createBranch(repository):
    archive, rest = repository.split('/', 1)
    category, branchname = repository.split('--', 2)[:2]

    try:
        archive = Archive.selectBy(name=archive)[0]
    except IndexError:
        raise RuntimeError, "No archive '%r' in DB" % (archive,)

    try:
        archnamespace = ArchNamespace.selectBy(
            archive=archive,
            category=category,
            branch=branch,
        )[0]
    except IndexError:
        archnamespace = ArchNamespace(
            archive=archive,
            category=category,
            branch=branchname,
            visible=False,
        )
    
    try:
        branch = Branch.selectBy(archnamespace=archnamespace)[0]
    except IndexError:
        branch = Branch(
            archnamespace=archnamespace,
            title=branchname,
            description='', # FIXME
        )
    
    return branch
        

    
class Manifest(SQLBase):
    """A manifest"""

    _table = 'Manifest'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                default=func.NOW),
    ]
    entries = MultipleJoin('ManifestEntry', joinColumn='manifest')

    def __iter__(self):
        return self.entries


class ManifestEntry(SQLBase):
    """A single entry in a manifest"""

    implements(IManifestEntry)
    
    _table = 'manifestentry'
    _columns = [
        ForeignKey(name='manifest', foreignKey='Manifest', dbName='manifest', 
                   notNull=True),
        IntCol(name='sequence', dbName='sequence', notNull=True),
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch', 
                   notNull=True),
        ForeignKey(name='changeset', foreignKey='Changeset', 
                   dbName='changeset'),
        IntCol(name='entrytype', dbName='entrytype', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        IntCol(name='patchon', dbName='patchon'),
        StringCol(name='dirname', dbName='dirname'),
    ]


class BranchRelationship(SQLBase):
    """A relationship between branches.
    
    e.g. "subject is a debianization-branch-of object"
    """

    _table = 'BranchRelationship'
    _columns = [
        ForeignKey(name='subject', foreignKey='Branch', dbName='subject', 
                   notNull=True),
        IntCol(name='label', dbName='label', notNull=True),
        ForeignKey(name='object', foreignKey='Branch', dbName='subject', 
                   notNull=True),
    ]

    def _get_src(self):
        return self.subject
    def _set_src(self, value):
        self.subject = value

    def _get_dst(self):
        return self.object
    def _set_dst(self, value):
        self.object = value

    def _get_labelText(self):
        # FIXME: There should be a better way to look up a schema
        #  item given its value
        return [br for br in dbschema.BranchRelationships
                if br == self.label][0]
        
# People Related sqlobject

class SoyuzEmailAddress(SQLBase):
    _table = 'EmailAddress'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('email', dbName='email', notNull=True),
        IntCol('status', dbName='status', notNull=True)
        ]

    def _statusname(self):
        for status in dbschema.EmailAddressStatus.items:
            if status.value == self.status:
                return status.title
        return 'Unknown (%d)' %self.status
    
    statusname = property(_statusname)



    
class GPGKey(SQLBase):
    _table = 'GPGKey'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('keyid', dbName='keyid', notNull=True),
        StringCol('fingerprint', dbName='fingerprint', notNull=True),
        StringCol('pubkey', dbName='pubkey', notNull=True),
        BoolCol('revoked', dbName='revoked', notNull=True)
##FIXME pending 'algorithm' and 'keysize' !!!
        ]


##FIXME: Experimental API with 4 attributes (includes also name instead just
##    value, title, description)
    def _algorithmname(self):
        for name, algorithm in dbschema.GPGKeyAlgorithms.items.mapping.items():
            if algorithm.value == self.algorithm:
                return name
        return 'Unknown (%d)' %self.algorithm
    
    algorithmname = property(_algorithmname)


    
class ArchUserID(SQLBase):
    _table = 'ArchUserID'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('archuserid', dbName='archuserid', notNull=True)
        ]
    
class WikiName(SQLBase):
    _table = 'WikiName'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('wiki', dbName='wiki', notNull=True),
        StringCol('wikiname', dbName='wikiname', notNull=True)
        ]

class JabberID(SQLBase):
    _table = 'JabberID'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('jabberid', dbName='jabberid', notNull=True)
        ]

class IrcID(SQLBase):
    _table = 'IrcID'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('network', dbName='network', notNull=True),
        StringCol('nickname', dbName='nickname', notNull=True)
        ]

class Membership(SQLBase):
    _table = 'Membership'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='SoyuzPerson', dbName='team',
                   notNull=True),
        IntCol('role', dbName='role', notNull=True),
        IntCol('status', dbName='status', notNull=True)
        ]

    def _rolename(self):
        for role in dbschema.MembershipRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role
    
    rolename = property(_rolename)

    def _statusname(self):
        for status in dbschema.MembershipStatus.items:
            if status.value == self.status:
                return status.title
        return 'Unknown (%d)' %self.status
    
    statusname = property(_statusname)

class TeamParticipation(SQLBase):
    _table = 'TeamParticipation'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='SoyuzPerson', dbName='team',
                   notNull=True)
        ]

# SQL Objects .... should be moved !!!!
class SoyuzPerson(SQLBase):
    """A person"""

    implements(ISoyuzPerson)

    _table = 'Person'
    _columns = [
        StringCol('givenname', dbName='givenname'),
        StringCol('familyname', dbName='familyname'),
        StringCol('displayname', dbName='displayname'),
        StringCol('password', dbName='password'),
        StringCol('name', dbName='name', notNull=True),
        ForeignKey(name='teamowner', dbName='teamowner',
                   foreignKey='SoyuzPerson'),
        StringCol('teamdescription', dbName='teamdescription'),
        IntCol('karma', dbName='karma'),
        DateTimeCol('karmatimestamp', dbName='karmatimestamp')
        ]

    
class SoyuzDistribution(SQLBase):

    implements(IDistribution)

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        StringCol('domainname', dbName='domainname'),
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson',
                   notNull=True)
        ]

class Release(SQLBase):

    implements(IRelease)

    _table = 'DistroRelease'
    _columns = [
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='SoyuzDistribution', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        StringCol('version', dbName='version', notNull=True),
        ForeignKey(name='components', dbName='components', foreignKey='Schema',
                   notNull=True),
        ForeignKey(name='sections', dbName='sections', foreignKey='Schema',
                   notNull=True),
        IntCol('releasestate', dbName='releasestate', notNull=True),
        DateTimeCol('datereleased', dbName='datereleased', notNull=True),
        ForeignKey(name='parentrelease', dbName='parentrelease',
                   foreignKey='Release', notNull=False),
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson',
                   notNull=True)
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
                FROM sourcepackagename, Sourcepackage,
                SourcepackageRelease, SourcepackageUpload
                WHERE sourcepackagename.id = sourcepackage.sourcepackagename
                AND SourcePackageUpload.sourcepackagerelease=
                                                  SourcePackageRelease.id
                AND SourcePackageRelease.sourcepackage = SourcePackage.id
                AND SourcePackageUpload.distrorelease = %s;""" % (self.id)

        db = SoyuzSourcePackage._connection._connection
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

        db = SoyuzBinaryPackage._connection._connection
        db_cursor = db.cursor()
        db_cursor.execute(q)
        return db_cursor.fetchall()[0][0]
                
    binarycount = property(binarycount)

#
# The basic implementation of a Sourcepackage object.
#
class Sourcepackage(SQLBase):
    implements(ISourcepackage)
    _columns = [
        ForeignKey(
                name='maintainer', dbName='maintainer', foreignKey='Person',
                notNull=True,
                ),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='manifest', dbName='manifest', foreignKey='Manifest',
                notNull=False,
                ),
        ForeignKey(
                name='distro', dbName='distro', foreignKey='Distribution',
                notNull=False,
                ),
        ForeignKey(
                name='sourcepackagename', dbName='sourcepackagename',
                foreignKey='SourcepackageName', notNull=True
                ),
        ]

    bugs = MultipleJoin(
            'SourcepackageBugAssignment', joinColumn='sourcepackage'
            )

    sourcepackagereleases = MultipleJoin(
            'SourcepackageRelease', joinColumn='sourcepackage'
            )

    def name(self):
        return self.sourcepackagename.name


#
# Basic implementation of a SourcepackageName object.
#
class SourcepackageName(SQLBase):
    _table='SourcepackageName'
    implements(ISourcepackage)
    _columns = [
        StringCol('name', notNull=True, unique=True),
        ]



""" Currently unneeded
class SourcepackageRelease(SQLBase):
    _table = 'SourcepackageRelease'
    _columns = [
        ForeignKey(
            name='sourcepackage', dbName='sourcepackage',
            foreignKey='Sourcepackage', notNull=True,
            ),
        IntCol(name='srcpackageformat', notNull=True,),
        ForeignKey(
            name='creator', dbName='creator',
            foreignKey='Person', notNull=True,
            ),
        StringCol('version', notNull=True),
        DatetimeCol('dateuploaded', notNull=True),
        IntCol('urgency', notNull=True),
        ForeignKey(
            name='dscsigningkey', dbName='dscsigningkey', notNull=False),
            )
        IntCol('component', notNull=False),
        StringCol('changelog', notNull=False),
        StringCol('builddepends', notNull=False),
        StringCol('builddependsindep', notNull=False),
        StringCol('architecturehintlist', notNull=False),
        StringCol('dsc', notNull=False),
        ]
"""



#
# Basic implementation of a Binarypackage object.
#
class Binarypackage(SQLBase):
    implements(IBinarypackage)
    _columns = [
        #ForeignKey(
        #        name='sourcepackagerelease', dbName='sourcepackagerelease',
        #        foreignKey='SourcepackageRelease', notNull=True,
        #        ),
        ForeignKey(
                name='binarypackagename', dbName='binarypackagename',
                foreignKey='BinarypackageName', notNull=True,
                ),
        StringCol('version', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        ForeignKey(
                name='build', dbName='build', foreignKey='Build', notNull=True,
                ),
        IntCol('binpackageformat', notNull=True),
        ForeignKey(
                name='component', dbName='component', foreignKey='Component',
                notNull=True,
                ),
        ForeignKey(
                name='section', dbName='section', foreignKey='Section',
                notNull=True,
                ),
        IntCol('priority'),
        StringCol('shlibdeps'),
        StringCol('recommends'),
        StringCol('suggests'),
        StringCol('conflicts'),
        StringCol('replaces'),
        StringCol('provides'),
        BoolCol('essential'),
        IntCol('installedsize'),
        StringCol('copyright'),
        StringCol('licence'),
        ]
    
    def _title(self):
        return '%s-%s' % (self.binarypackagename.name, self.version)
    title = property(_title, None)

class BinarypackageName(SQLBase):
    implements(IBinarypackageName)
    _table = 'BinarypackageName'
    _columns = [
        StringCol('name', notNull=True, unique=True),
        ]
    binarypackages = MultipleJoin(
            'Binarypackage', joinColumn='binarypackagename'
            )

