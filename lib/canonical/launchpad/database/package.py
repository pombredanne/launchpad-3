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
                                           ISourcepackage, IBinarypackage, \
                                           ISourcepackageName, IBinarypackageName

from canonical.launchpad.database import Product, Project
from canonical.launchpad.database.person import Person


class SoyuzPackagePublishing(SQLBase):

    _table = 'PackagePublishing'
    
    _columns = [
        ForeignKey(name='binaryPackage', foreignKey='Binarypackage', 
                   dbName='binarypackage', notNull=True),
        ForeignKey(name='distroArchrelease', dbName='distroArchrelease',
                   foreignKey='SoyuzDistroArchRelease', notNull=True),
        ForeignKey(name='component', dbName='component',
                   foreignKey='SoyuzComponent', notNull=True),
        ForeignKey(name='section', dbName='section', foreignKey='SoyuzSection',
                   notNull=True),
        IntCol('priority', dbName='priority', notNull=True),
    ]


class Binarypackage(SQLBase):
    implements(IBinarypackage)
    _table = 'BinaryPackage'
    _columns = [
        ForeignKey(name='binarypackagename', dbName='binarypackagename', 
                   foreignKey='BinarypackageName', notNull=True),
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
        last = list(SourcePackageRelease.select(
            'SourcepackagePublishing.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcepackagePublishing.status = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id, self.build.sourcepackagerelease.sourcepackage.id,dbschema.PackagePublishingStatus.SUPERCEDED)
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


class BinarypackageName(SQLBase):
    _table = 'BinaryPackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
    ]

    # Got from BinaryPackageName class
    binarypackages = MultipleJoin(
            'Binarypackage', joinColumn='binarypackagename'
            )
    ####

class SourcePackageRelease(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(ISourcePackageRelease)

    _table = 'SourcePackageRelease'
    _columns = [
        ForeignKey(name='sourcepackage', foreignKey='Sourcepackage',
                   dbName='sourcepackage', notNull=True),
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

        return Binarypackage.select(query)
        
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

class Sourcepackage(SQLBase):
    """A source package, e.g. apache2."""

    implements(ISourcepackage)

    _table = 'SourcePackage'

    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcepackageName',
                   dbName='sourcepackagename', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest',
                          default=None)
    distro = ForeignKey(foreignKey='Distribution', dbName='distro')

    releases = MultipleJoin('SourcePackageRelease',
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
        return SourcePackageRelease.selectBy(version=version)[0]

    def uploadsByStatus(self, distroRelease, status):
        uploads = list(SourcePackageRelease.select(
            'SourcepackagePublishing.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcepackagePublishing.status = %d'
            % (distroRelease.id, self.id, status)
        ))

        if uploads:
            return uploads[0]
        else:
            return None

    def proposed(self, distroRelease):
        return self.uploadsByStatus(distroRelease,
                                    dbschema.PackagePublishingStatus.PROPOSED)

    def current(self, distroRelease):
        """Currently published releases of this package for a given distro.
        
        :returns: iterable of SourcePackageReleases
        """
        sourcepackagereleases = SourcePackageRelease.select(
            'SourcepackagePublishing.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackagePublishing.distrorelease = %d'
            ' AND SourcepackageRelease.sourcepackage = %d'
            ' AND SourcepackagePublishing.status = %d'
            % (distroRelease.id, self.id, dbschema.PackagePublishingStatus.PUBLISHED)
        )

        return sourcepackagereleases

    def lastversions(self, distroRelease):
        last = list(SourcePackageRelease.select(
            'SourcepackagePublishing.sourcepackagerelease=SourcepackageRelease.id'
            ' AND SourcepackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcepackagePublishing.status = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id, self.id,dbschema.PackagePublishingStatus.SUPERCEDED)
        ))

        if last:
            return last
        else:
            return None


class SourcepackageName(SQLBase):

    implements(ISourcepackageName)

    _table = 'SourcepackageName'

    name = StringCol(dbName='name', notNull=True)
