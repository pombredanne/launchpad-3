# Python imports
from sets import Set

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackage, \
     ISourcePackageSet
    
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
     VSourcePackageReleasePublishing

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
                 % (distroRelease.id, self.id, status.value))

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
                                    dbschema.PackagePublishingStatus.SUPERSEDED,
                                    do_sort=True)


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
        from canonical.launchpad.database.sourcepackageindistro import \
             SourcePackageInDistro

        return SourcePackageInDistro.select("maintainer = %d" % personID,
                                            orderBy='name')

