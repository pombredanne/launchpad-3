# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func
from canonical.database.sqlbase import SQLBase
from canonical.lp import dbschema

# Soyuz interfaces
from canonical.soyuz.interfaces import ISourcePackageRelease, IManifestEntry
from canonical.soyuz.interfaces import IBranch, IChangeset
from canonical.soyuz.interfaces import ISourcePackage, ISoyuzPerson
from canonical.soyuz.interfaces import IBinaryPackage


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
        ForeignKey(name='sourcepackagerelease', dbName='sourcepackagerelease',
                   foreignKey='SoyuzSourcePackageRelease', notNull=True),
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


class SoyuzBinaryPackageName(SQLBase):
    _table = 'BinaryPackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
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
    ]
    releases = MultipleJoin('SoyuzSourcePackageRelease',
                            joinColumn='sourcepackage')

    def name(self):
        return self.sourcepackagename.name
    name = property(name)

    def title(self):
        import warnings
        warnings.warn("Use SoyuzSourcePackage.shortdesc instead of .title",
                      DeprecationWarning)
        return self.shortdesc
    title = property(title)

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
        sourcepackagereleases = list(SoyuzSourcePackageRelease.select(
            'SourcePackageUpload.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackageUpload.distrorelease = %d'
            ' AND SourcepackageRelease.sourcepackage = %d'
            ' AND SourcePackageUpload.uploadstatus = %d'
            % (distroRelease.id, self.id, dbschema.SourceUploadStatus.PUBLISHED)
        ))

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
    ]

    builds = MultipleJoin('SoyuzBuild', joinColumn='sourcepackagerelease')

    def architecturesReleased(self, distroRelease):
        archReleases = SoyuzDistroArchRelease.select(
            'PackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND PackagePublishing.binarypackage = BinaryPackage.id '
            'AND BinaryPackage.sourcepackagerelease = %d'
            % (distroRelease.id, self.id)
        )
        return archReleases


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
    from canonical.arch.database import Archive, Branch, ArchNamespace

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
        # FIXME: There should be a better way to look up a schema item given its
        #        value
        return [br for br in dbschema.BranchRelationships
                if br == self.label][0]
        

class SoyuzProduct(SQLBase):

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='Project', dbName='project',
                   notNull=True),
        ForeignKey(name='owner', foreignKey='SoyuzPerson', dbName='owner',
                   notNull=True),
        StringCol('name', dbName='name', notNull=True),
        # TODO: remove default on displayname and shortdesc
        StringCol('displayname', dbName='displayname', notNull=True,
                  default=''),
        StringCol('title', dbName='title', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True, default=''),
        StringCol('description', dbName='description', notNull=True),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                    default="NOW"),
        StringCol('homepageurl', dbName='homepageurl'),
        StringCol('screenshotsurl'),
        StringCol('wikiurl'),
        StringCol('programminglang'),
        StringCol('downloadurl'),
        StringCol('lastdoap'),
        ]

        

class SoyuzProject(SQLBase):

    _table = 'Project'

    _columns = [
        ForeignKey(name='owner', foreignKey='SoyuzPerson', dbName='owner',
                   notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('displayname', dbName='displayname', notNull=True,
                  default=""),
        StringCol('title', dbName='title', notNull=True, default=""),
        StringCol('shortdesc', dbName='shortdesc', notNull=True, default=""),
        StringCol('description', dbName='description', notNull=True,
                  default=""),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                    default="NOW"),
        StringCol('homepageurl', dbName='homepageurl'),
    ]

# People Related sqlobject

class SoyuzEmailAddress(SQLBase):
    _table = 'EmailAddress'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('email', dbName='email', notNull=True),
        IntCol('status', dbName='status', notNull=True)
        ]
    
class GPGKey(SQLBase):
    _table = 'GPGKey'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        StringCol('keyid', dbName='keyid', notNull=True),
        StringCol('fingerprint', dbName='fingerprint', notNull=True),
        StringCol('pubkey', dbName='pubkey', notNull=True),
        BoolCol('revoked', dbName='revoked', notNull=True)
        ]
    
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

class TeamParticipation(SQLBase):
    _table = 'TeamParticipation'
    _columns = [
        ForeignKey(name='person', foreignKey='SoyuzPerson', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='SoyuzPerson', dbName='team',
                   notNull=True)
        ]



# arch-tag: 6c76cb93-edf7-4019-9af4-53bfeb279194
