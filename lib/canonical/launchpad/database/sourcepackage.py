# Python imports
import re
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
                                           ISourcePackageReleasePublishing, \
                                           ISourcePackage, \
                                           ISourcePackageName, \
                                           ISourcePackageSet

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

    distro            = ForeignKey(foreignKey='Distribution', dbName='distro')
    manifest          = ForeignKey(foreignKey='Manifest', dbName='manifest')
    maintainer        = ForeignKey(foreignKey='Person', dbName='maintainer', 
                                   notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)

    releases = MultipleJoin('SourcePackageRelease', joinColumn='sourcepackage')
    bugs     = MultipleJoin('SourcePackageBugAssignment', 
                            joinColumn='sourcepackage')

    #
    # Properties
    #
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

    #
    # Methods
    #
    def bugsCounter(self):
        # XXXkiko: move to bugassignment?
        from canonical.launchpad.database.bugassignment import \
            SourcePackageBugAssignment

        ret = [len(self.bugs)]

        get = SourcePackageBugAssignment.selectBy
        severities = [
            dbschema.BugSeverity.CRITICAL,
            dbschema.BugSeverity.MAJOR,
            dbschema.BugSeverity.NORMAL,
            dbschema.BugSeverity.MINOR,
            dbschema.BugSeverity.WISHLIST,
            dbschema.BugAssignmentStatus.FIXED,
            dbschema.BugAssignmentStatus.ACCEPTED,
        ]
        for severity in severities:
            n = get(severity=int(severity), sourcepackageID=self.id).count()
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
                                    dbschema.PackagePublishingStatus.PUBLISHED)

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
        results = self.table.select("SourcePackage.id = \
                                     SourcePackageBugAssignment.sourcepackage",
                                     clauseTables=['SourcePackage',
                                     'SourcePackageBugAssignment'])
        for pkg in results:
            pkgset.add(pkg)
        return pkgset

    def getSourcePackages(self, distroreleaseID):
        """Returns a set of SourcePackage in a DistroRelease"""
        query = ('distrorelease = %d ' 
                 % (distroreleaseID)
                 )

        return SourcePackageInDistro.select(query, orderBy='name')

    def findByName(self, distroreleaseID, pattern):
        """Returns a set o sourcepackage that matchs pattern
        inside a distrorelease"""

        pattern = quote("%%" + pattern.replace('%', '%%') + "%%")
        query = ('distrorelease = %d AND '
                 '(name ILIKE %s OR shortdesc ILIKE %s)' %
                 (distroreleaseID, pattern, pattern))
        return VSourcePackageReleasePublishing.select(query, orderBy='name')

    def getByName(self, distroreleaseID, name):
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

    
    def getByPersonID(self, personID):
        # XXXkiko: we should allow supplying a distrorelease here and
        # get packages by distro
        return SourcePackageInDistro.select("maintainer = %d" % personID,
                                            orderBy='name')
   

class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True)


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

    def linkified_changelog(self):
        # XXX: salgado: No bugtracker URL should be hardcoded.
        sourcepkgname = self.sourcepackage.sourcepackagename.name
        deb_bugs = 'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug='
        warty_bugs = 'https://bugzilla.ubuntu.com/show_bug.cgi?id='
        changelog = re.sub(r'%s \(([^)]+)\)' % sourcepkgname,
                           r'%s (<a href="../\1">\1</a>)' % sourcepkgname,
                           self.changelog)
        changelog = re.sub(r'([Ww]arty#)([0-9]+)', 
                           r'<a href="%s\2">\1\2</a>' % warty_bugs,
                           changelog)
        changelog = re.sub(r'[^(W|w)arty]#([0-9]+)', 
                           r'<a href="%s\1">#\1</a>' % deb_bugs,
                           changelog)
        return changelog

    linkified_changelog = property(linkified_changelog)

    binaries = property(binaries)

    pkgurgency = property(_urgency)

    #
    # Methods
    #
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

