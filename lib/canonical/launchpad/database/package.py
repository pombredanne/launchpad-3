# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageRelease, \
                                           ISourcePackage, \
                                           IBinaryPackage, \
                                           ISourcepackage, IBinarypackage, \
                                           ISourcepackageName, IBinarypackageName

from canonical.launchpad.database import Product, Project
from canonical.launchpad.database import Archive, Branch, ArchNamespace
from canonical.launchpad.database.person import Person

# This import has been moved to SoyuzSourcePackageRelease.architecturesReleased
# to avoid a circular import.
##from canonical.launchpad.database.distro import SoyuzDistroArchRelease


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

    def _title(self):
        return '%s-%s' % (self.binarypackagename.name, self.version)
    title = property(_title, None)


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

    # Got from BinaryPackageName class
    binarypackages = MultipleJoin(
            'Binarypackage', joinColumn='binarypackagename'
            )
    ####

class SoyuzBuild(SQLBase):
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
                   foreignKey='SoyuzSourcePackageRelease', notNull=True),

    ]


class SoyuzSourcePackageRelease(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(ISourcePackageRelease)

    _table = 'SourcePackageRelease'
    _columns = [
        ForeignKey(name='sourcepackage', foreignKey='SoyuzSourcePackage',
                   dbName='sourcepackage', notNull=True),
        IntCol('srcpackageformat', dbName='srcpackageformat', notNull=True),
        ForeignKey(name='creator', foreignKey='Person', dbName='creator'),
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
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.distro import SoyuzDistroArchRelease

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


class SoyuzSourcePackage(SQLBase):
    """A source package, e.g. apache2."""

    implements(ISourcePackage)

    _table = 'SourcePackage'
    _columns = [
        ForeignKey(name='maintainer', foreignKey='Person',
                   dbName='maintainer', notNull=True),
        ForeignKey(name='sourcepackagename',
                   foreignKey='SoyuzSourcePackageName',
                   dbName='sourcepackagename', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='manifest', foreignKey='Manifest',
                   dbName='manifest', default=None),
        ForeignKey(name='distro', foreignKey='Distribution', dbName='distro'),
    ]
    releases = MultipleJoin('SoyuzSourcePackageRelease',
                            joinColumn='sourcepackage')

    # Got from the old SourcePackage class
    bugs = MultipleJoin(
            'SourcepackageBugAssignment', joinColumn='sourcepackage'
            )

    sourcepackagereleases = MultipleJoin(
            'SourcepackageRelease', joinColumn='sourcepackage'
            )
    ####

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

    
#
#FIX ME

class Sourcepackage(SoyuzSourcePackage):
    pass

class SourcepackageName(SoyuzSourcePackageName):
    pass

class Binarypackage(SoyuzBinaryPackage):
    pass

class BinarypackageName(SoyuzBinaryPackageName):
    pass

