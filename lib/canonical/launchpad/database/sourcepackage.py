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
                                           ISourcePackageName, \
                                           ISourcePackageContainer

from canonical.launchpad.database.product import Product
from canonical.launchpad.database.binarypackage import BinaryPackage


class SourcePackage(SQLBase):
    """A source package, e.g. apache2."""

    implements(ISourcePackage)

    _table = 'SourcePackage'

    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
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
            'SourcePackageBugAssignment', joinColumn='sourcepackage'
            )

    sourcepackagereleases = MultipleJoin(
            'SourcePackageRelease', joinColumn='sourcepackage'
            )
    ####
    def bugsCounter(self):
        from canonical.launchpad.database.bugassignment import SourcePackageBugAssignment

        get = SourcePackageBugAssignment.selectBy
        all = len(self.bugs)
        critical = get(severity=int(dbschema.BugSeverity.CRITICAL),
                       sourcepackageID = self.id).count()
        important = get(severity = int(dbschema.BugSeverity.MAJOR),
                       sourcepackageID = self.id).count()
        normal = get(severity = int(dbschema.BugSeverity.NORMAL),
                       sourcepackageID = self.id).count()
        minor = get(severity = int(dbschema.BugSeverity.MINOR),
                       sourcepackageID = self.id).count()
        wishlist = get(severity = int(dbschema.BugSeverity.WISHLIST),
                       sourcepackageID = self.id).count()
        fixed = get(bugstatus = int(dbschema.BugAssignmentStatus.CLOSED),
                       sourcepackageID = self.id).count()
        pending = get(bugstatus = int(dbschema.BugAssignmentStatus.OPEN),
                       sourcepackageID = self.id).count()

        return (all, critical, important, normal, minor, wishlist, fixed, pending)


    def name(self):
        return self.sourcepackagename.name
    name = property(name)

    def product(self):
        try:
            clauseTables = ('Packaging', 'Product')
            return Product.select("Product.id = Packaging.product AND "
                                  "Packaging.sourcepackage = %d"
                                  % self.id, clauseTables=clauseTables)[0]
        except IndexError:
            # No corresponding product
            return None
    product = property(product)

    def getManifest(self):
        return self.manifest

    def getRelease(self, version):
        return SourcePackageRelease.selectBy(version=version)[0]

    def uploadsByStatus(self, distroRelease, status):
        clauseTables = ('SourcePackagePublishing', 'SourcePackageRelease')
        uploads = list(SourcePackageRelease.select(
            'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id'
            ' AND SourcePackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackagePublishing.status = %d'
            % (distroRelease.id, self.id, status), clauseTables=clauseTables))

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
        clauseTables = ('SourcePackagePublishing', 'SourcePackageRelease')
        sourcepackagereleases = SourcePackageRelease.select(
            'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id'
            ' AND SourcePackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackagePublishing.status = %d'
            % (distroRelease.id, self.id, dbschema.PackagePublishingStatus.PUBLISHED),
            clauseTables=clauseTables)

        return sourcepackagereleases

    def lastversions(self, distroRelease):
        clauseTables=('SourcePackagePublishing', 'SourcePackageRelease')

        last = list(SourcePackageRelease.select(
            'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id'
            ' AND SourcePackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackagePublishing.status = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id, self.id,dbschema.PackagePublishingStatus.SUPERCEDED)
        , clauseTables=clauseTables))

        if last:
            return last
        else:
            return None

    #
    # SourcePackage Class Methods
    #

    def findSourcesByName(klass, distrorelease, pattern):
        """Search for SourcePackages in a distrorelease that matches"""
        clauseTables=('SourcePackagePublishing', 'SourcePackage',
                      'SourcePackageName', 'SourcePackageRelease')
        pattern = pattern.replace('%', '%%')
        query = ('SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
                  'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
                  'AND SourcePackagePublishing.distrorelease = %d '
                  'AND SourcePackage.sourcepackagename = SourcePackageName.id'
                  % (distrorelease.id) +
                 ' AND (SourcePackageName.name ILIKE %s'
                 % quote('%%' + pattern + '%%')
                 + ' OR SourcePackage.shortdesc ILIKE %s)'
                 % quote('%%' + pattern + '%%'))
        
        # XXX: Daniel Debonzi 2004-10-19
        # Returning limited results until
        # sql performanse issues been solved
        return klass.select(query,
                            clauseTables=clauseTables,
                            orderBy='sourcepackagename.name')

    findSourcesByName = classmethod(findSourcesByName)



class SourcePackageContainer(object):
    """A container for SourcePackage objects."""

    implements(ISourcePackageContainer)
    table = SourcePackage

    #
    # We need to return a SourcePackage given a name. For phase 1 (warty)
    # we can assume that there is only one package with a given name, but
    # later (XXX) we will have to deal with multiple source packages with
    # the same name.
    #
    def __getitem__(self, name):
        clauseTables = ('SourcePackageName', 'SourcePackage')
        return self.table.select("SourcePackage.sourcepackagename = \
        SourcePackageName.id AND SourcePackageName.name = %s" %     \
        quote(name))[0]

    def __iter__(self):
        for row in self.table.select():
            yield row

    def withBugs(self):
        pkgset = Set()
        results = self.table.select("SourcePackage.id = \
                                     SourcePackageBugAssignment.sourcepackage")
        for pkg in results:
            pkgset.add(pkg)
        return pkgset
        



class SourcePackageName(SQLBase):

    implements(ISourcePackageName)

    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True)



class SourcePackageRelease(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(ISourcePackageRelease)

    _table = 'SourcePackageRelease'
    _columns = [
        ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
                   dbName='sourcepackage', notNull=True),
        ForeignKey(name='creator', foreignKey='Person', dbName='creator'),
        StringCol('version', dbName='version'),
        DateTimeCol('dateuploaded', dbName='dateuploaded', notNull=True,
                    default='NOW'),
        IntCol('urgency', dbName='urgency', notNull=True),
        ForeignKey(name='component', foreignKey='Component', dbName='component'),
        StringCol('changelog', dbName='changelog'),
        StringCol('builddepends', dbName='builddepends'),
        StringCol('builddependsindep', dbName='builddependsindep'),
        ForeignKey(name='section', foreignKey='Section', dbName='section'),
    ]

    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease')

    def architecturesReleased(self, distroRelease):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.distro import DistroArchRelease
        clauseTables = ('PackagePublishing', 'BinaryPackage', 'Build')
        
        archReleases = Set(DistroArchRelease.select(
            'PackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND PackagePublishing.binarypackage = BinaryPackage.id '
            'AND BinaryPackage.build = Build.id '
            'AND Build.sourcepackagerelease = %d'
            % (distroRelease.id, self.id),
            clauseTables=clauseTables))
        return archReleases

    def _urgency(self):
        for urgency in dbschema.SourcePackageUrgency.items:
            if urgency.value == self.urgency:
                return urgency.title
        return 'Unknown (%d)' %self.urgency

    def binaries(self):
        clauseTables = ('SourcePackageRelease', 'BinaryPackage', 'Build')
        
        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i'
                 %self.id)

        return BinaryPackage.select(query, clauseTables=clauseTables)
        
    binaries = property(binaries)

    pkgurgency = property(_urgency)


    #
    # SourcePackageRelease Class Methods
    #
    
    def getByName(klass, distrorelease, name):
        """Get A SourcePackageRelease in a distrorelease by its name"""
        clauseTables = ('SourcePackage', 'SourcePackagePublishing',
                        'SourcePackageName')

        # XXX: (mult_results) Daniel Debonzi 2004-10-13
        # What about multiple results?
        #(which shouldn't happen here...)
        query = ('SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
                 'AND SourcePackagePublishing.distrorelease = %d '
                 'AND SourcePackage.sourcepackagename = SourcePackageName.id'
                 ' AND SourcePackageName.name = %s'
                 % (distrorelease.id, quote(name))  )


        return klass.select(query, clauseTables=clauseTables)[0]
    getByName = classmethod(getByName)

    def getReleases(klass, distrorelease):
        """Get SourcePackageReleases in a distrorelease"""
        clauseTables = ('SourcePackagePublishing', 'Sourcepackage',
                        'SourcePackageName')

        query = ('SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
                 'AND SourcePackagePublishing.distrorelease = %d '
                 'AND SourcePackage.sourcepackagename = SourcePackageName.id'
                 % (distrorelease.id))
        
        # FIXME: (distinct_query) Daniel Debonzi - 2004-10-13
        # the results are NOT UNIQUE (DISTINCT)
        
        # FIXME: (SQLObject_Selection+batching) Daniel Debonzi - 2004-10-13
        # The selection is limited here because batching and SQLObject
        # selection still not working properly. Now the days for each
        # page showing BATCH_SIZE results the SQLObject makes queries
        # for all the related things available on the database which
        # presents a very slow result.
        return klass.select(query,
                            clauseTables=clauseTables,
                            orderBy='sourcepackagename.name')
    getReleases = classmethod(getReleases)


    def selectByVersion(klass, sourcereleases, version):
        """Select from SourcePackageRelease.SelectResult that have
        version=version"""

        clauseTables = ('SourcePackagePublishing', 'Build',
                        'BinaryPackage')
        
        query = sourcereleases.clause + \
                ' AND SourcePackageRelease.version = %s' %quote(version)

        return klass.select(query, clauseTables=clauseTables)

    selectByVersion = classmethod(selectByVersion)

    def selectByBinaryVersion(klass, sourcereleases, version):
        """Select from SourcePackageRelease.SelectResult that have
        BinaryPackage.version=version"""
        clauseTables = ('SourcepackagePublishing','BinaryPackage', 'Build')
        
        query = sourcereleases.clause + \
                (' AND Build.id = BinaryPackage.build'
                 ' AND Build.sourcepackagerelease = SourcePackageRelease.id'
                 ' AND BinaryPackage.version = %s' %quote(version)
                )

        return klass.select(query, clauseTables=clauseTables)

    selectByBinaryVersion = classmethod(selectByBinaryVersion)


    def getByPersonID(klass, personID):
        clauseTables = ('SourcePackagePublishing', 'SourcePackageName',
                        'SourcePackage')
        query = ('''SourcePackagePublishing.sourcepackagerelease = 
                        SourcePackageRelease.id 
                    AND SourcePackageName.id = SourcePackage.sourcepackagename
                    AND SourcePackageRelease.sourcepackage = SourcePackage.id 
                    AND SourcePackage.maintainer = %i''' % personID)
        # FIXME: (sourcename_order) Daniel Debonzi 2004-10-13
        # ORDER by SourcePackagename
        # The result should be ordered by SourcePackageName
        # but seems that is it not possible
        return klass.select(query,
                            clauseTables=clauseTables,
                            orderBy='sourcepackagename.name')
    getByPersonID = classmethod(getByPersonID)
        




# XXX Mark Shuttleworth: this is somewhat misleading as there
# will likely be several versions of a source package with the
# same name, please consider getSourcePackages() 21/10/04
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

