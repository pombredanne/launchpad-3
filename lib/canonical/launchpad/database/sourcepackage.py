# Python imports
from sets import Set

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageRelease, \
                                           ISourcePackageReleasePublishing, \
                                           ISourcePackage, \
                                           ISourcePackageName, \
                                           ISourcePackageNameSet, \
                                           ISourcePackageSet, \
                                           ISourcePackageInDistroSet, \
                                           ISourcePackageUtility

from canonical.launchpad.database.product import Product
from canonical.launchpad.database.binarypackage import BinaryPackage


class SourcePackage(SQLBase):
    """A source package, e.g. apache2."""
    implements(ISourcePackage)
    _table = 'SourcePackage'

    #
    # Columns
    #
    shortdesc   = StringCol(dbName='shortdesc', notNull=True)
    description = StringCol(dbName='description', notNull=True)

    srcpackageformat = IntCol(dbName='srcpackageformat', notNull=True)

    distro            = ForeignKey(foreignKey='Distribution', 
                                   dbName='distro')
    manifest          = ForeignKey(foreignKey='Manifest', dbName='manifest')
    maintainer        = ForeignKey(foreignKey='Person', dbName='maintainer', 
                                   notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)

    releases = MultipleJoin('SourcePackageRelease', joinColumn='sourcepackage')

    #
    # Properties
    #
    def name(self):
        return self.sourcepackagename.name

    name = property(name)

    def bugtasks(self):
        querystr = ("BugTask.distribution = %i AND "
                    "BugTask.sourcepackagename = %i")
        querystr = querystr % (self.distro, self.sourcepackagename)
        return BugTask.select(querystr)

    bugtasks = property(bugtasks)

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

    #
    # Methods
    #
    def bugsCounter(self):
        from canonical.launchpad.database.bugtask import BugTask

        ret = [len(self.bugs)]

        get = BugTask.selectBy
        severities = [
            dbschema.BugSeverity.CRITICAL,
            dbschema.BugSeverity.MAJOR,
            dbschema.BugSeverity.NORMAL,
            dbschema.BugSeverity.MINOR,
            dbschema.BugSeverity.WISHLIST,
            dbschema.BugTaskStatus.FIXED,
            dbschema.BugTaskStatus.ACCEPTED,
        ]
        for severity in severities:
            n = get(severity=int(severity), sourcepackagenameID=self.sourcepackagename.id).count()
            ret.append(n)
        return ret

    def getRelease(self, version):
        ret = VSourcePackageReleasePublishing.selectBy(version=version)
        assert ret.count() == 1
        return ret[0]

    def uploadsByStatus(self, distroRelease, status, do_sort=False):
        query = (' distrorelease = %d '
                 ' AND sourcepackage = %d'
                 ' AND publishingstatus = %d'
                 % (distroRelease.id, self.id, status))

        if do_sort:
            # XXX: Daniel Debonzi 2004-12-01
            # Check if the orderBy is working properly
            # as soon as we have enought data in db.
            # Anyway, seems to be ok
            return VSourcePackageReleasePublishing.select(query,
                                                  orderBy='dateuploaded')
        
        return VSourcePackageReleasePublishing.select(query)

    def proposed(self, distroRelease):
        return self.uploadsByStatus(distroRelease,
                                    dbschema.PackagePublishingStatus.PROPOSED)

    def current(self, distroRelease):
        """Currently published releases of this package for a given distro.
        
        :returns: iterable of SourcePackageReleases
        """
        return self.uploadsByStatus(distroRelease, 
                                    dbschema.PackagePublishingStatus.PUBLISHED)[0]

    def lastversions(self, distroRelease):
        return self.uploadsByStatus(distroRelease, 
                                    dbschema.PackagePublishingStatus.SUPERCEDED,
                                    do_sort=True)


class SourcePackageInDistro(SourcePackage):
    """
    Represents source packages that have releases published in the
    specified distribution. This view's contents are uniqued, for the
    following reason: a certain package can have multiple releases in a
    certain distribution release.
    """
    _table = 'VSourcePackageInDistro'
   
    #
    # Columns
    #
    name = StringCol(dbName='name', notNull=True)

    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')

    releases = MultipleJoin('SourcePackageRelease', joinColumn='sourcepackage')


class SourcePackageSet(object):
    """A set for SourcePackage objects."""

    implements(ISourcePackageSet)
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
        quote(name), clauseTables=clauseTables)[0]

    def __iter__(self):
        for row in self.table.select():
            yield row

    def withBugs(self):
        pkgset = Set()
        results = self.table.select(
            "SourcePackage.sourcepackagename = BugTask.sourcepackagename AND"
            "SourcePackage.distro = BugTask.distribution",
            clauseTables=['SourcePackage', 'BugTask'])
        for pkg in results:
            pkgset.add(pkg)
        return pkgset

    def getByPersonID(self, personID):
        # XXXkiko: we should allow supplying a distrorelease here and
        # get packages by distro
        return SourcePackageInDistro.select("maintainer = %d" % personID,
                                            orderBy='name')

class SourcePackageInDistroSet(object):
    """A Set of SourcePackages in a given DistroRelease"""
    implements(ISourcePackageInDistroSet)
    def __init__(self, distrorelease):
        """Take the distrorelease when it makes part of the context"""
        self.distrorelease = distrorelease

    def findPackagesByName(self, pattern, fti=False):
        srcutil = getUtility(ISourcePackageUtility)
        return srcutil.findByNameInDistroRelease(self.distrorelease.id,
                                                 pattern, fti)

    def __iter__(self):
        plublishing_status = dbschema.PackagePublishingStatus.PUBLISHED.value
        
        query = ('distrorelease = %d'
                 % (self.distrorelease.id))
        
        return iter(SourcePackageInDistro.select(query,
                                                 orderBy='VSourcePackageInDistro.name',
                                                 distinct=True))

    def __getitem__(self, name):
        plublishing_status = dbschema.PackagePublishingStatus.PUBLISHED.value

        query = ('distrorelease = %d AND publishingstatus=%d AND name=%s'
                 % (self.distrorelease.id, plublishing_status, quote(name)))

        try:
            return VSourcePackageReleasePublishing.select(query)[0]
        except IndexError:
            raise KeyError, name
            
            
class SourcePackageUtility(object):
    """A utility for sourcepackages"""
    implements(ISourcePackageUtility)

    def findByNameInDistroRelease(self, distroreleaseID,
                                  pattern, fti=False):
        """Returns a set o sourcepackage that matchs pattern
        inside a distrorelease"""

        clauseTables = ()

        pattern = pattern.replace('%', '%%')

        if fti:
            clauseTables = ('SourcePackage',)
            query = ('VSourcePackageReleasePublishing.sourcepackage = '
                     'SourcePackage.id AND '
                     'distrorelease = %d AND '
                     '(name ILIKE %s OR SourcePackage.fti @@ ftq(%s))'
                     %(distroreleaseID,
                       quote('%%'+pattern+'%%'),
                       quote(pattern))
                     )

        else:
            query = ('distrorelease = %d AND '
                     'name ILIKE %s '
                     % (distroreleaseID, quote('%%'+pattern+'%%'))
                     )

        return VSourcePackageReleasePublishing.select(query, orderBy='name',
                                                      clauseTables=clauseTables)

    def getByNameInDistroRelease(self, distroreleaseID, name):
        """Returns a SourcePackage by its name"""

        query = ('distrorelease = %d ' 
                 ' AND name = %s'
                 % (distroreleaseID, quote(name))
                 )

        return SourcePackageInDistro.select(query, orderBy='name')[0]

    def getSourcePackageRelease(self, sourcepackageID, version):
        table = VSourcePackageReleasePublishing 
        return table.select("sourcepackage = %d AND version = %s"
                            % (sourcepackageID, quote(version)))

class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True, unique=True,
        alternateID=True)

    def __unicode__(self):
        return self.name


class SourcePackageNameSet(object):
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        try:
            return SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def __iter__(self):
        for sourcepackagename in SourcePackageName.select():
            yield sourcepackagename


class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(foreignKey='Person', dbName='creator')
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackage = ForeignKey(foreignKey='SourcePackage',
                               dbName='sourcepackage')
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')

    urgency = IntCol(dbName='urgency', notNull=True)
    dateuploaded = DateTimeCol(dbName='dateuploaded', notNull=True,
                               default='NOW')

    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = StringCol(dbName='changelog')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    architecturehintlist = StringCol(dbName='architecturehintlist')

    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease')

    #
    # Properties
    #
    def _urgency(self):
        for urgency in dbschema.SourcePackageUrgency.items:
            if urgency.value == self.urgency:
                return urgency.title
        return 'Unknown (%d)' %self.urgency

    def binaries(self):
        clauseTables = ('SourcePackageRelease', 'BinaryPackage', 'Build')

        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i' % self.id)

        return BinaryPackage.select(query, clauseTables=clauseTables)

    binaries = property(binaries)

    pkgurgency = property(_urgency)

    #
    # Methods
    #
    def architecturesReleased(self, distroRelease):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.soyuz import DistroArchRelease
        clauseTables = ('PackagePublishing', 'BinaryPackage', 'Build')
        
        archReleases = Set(DistroArchRelease.select(
            'PackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND PackagePublishing.binarypackage = BinaryPackage.id '
            'AND BinaryPackage.build = Build.id '
            'AND Build.sourcepackagerelease = %d'
            % (distroRelease.id, self.id), clauseTables=clauseTables))
        return archReleases


class VSourcePackageReleasePublishing(SourcePackageRelease):
    implements(ISourcePackageReleasePublishing)
    _table = 'VSourcePackageReleasePublishing'

    # XXXkiko: IDs in this table are *NOT* unique!
    # XXXkiko: clean up notNulls
    datepublished = DateTimeCol(dbName='datepublished')
    publishingstatus = IntCol(dbName='publishingstatus', notNull=True)

    name = StringCol(dbName='name', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    componentname = StringCol(dbName='componentname', notNull=True)

    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    #XXX: salgado: wtf is this?
    #MultipleJoin('Build', joinColumn='sourcepackagerelease'),

    def __getitem__(self, version):
        """Get a  SourcePackageRelease"""
        table = VSourcePackageReleasePublishing 
        try:            
            return table.select("sourcepackage = %d AND version = %s"
                                % (self.sourcepackage.id, quote(version)))[0]
        except IndexError:
            raise KeyError, 'Version Not Found'
        
def createSourcePackage(name, maintainer=0):
    # FIXME: maintainer=0 is a hack.  It should be required (or the DB shouldn't
    #        have NOT NULL on that column).
    return SourcePackage(
        name=name, 
        maintainer=maintainer,
        title='', # FIXME
        description='', # FIXME
    )

