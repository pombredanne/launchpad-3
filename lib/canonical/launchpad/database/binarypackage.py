# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackage, \
                                           IBinaryPackageName



class BinaryPackage(SQLBase):
    implements(IBinaryPackage)
    _table = 'BinaryPackage'
    binarypackagename = ForeignKey(dbName='binarypackagename', 
                   foreignKey='BinaryPackageName', notNull=True),
    version = StringCol(dbName='version', notNull=True),
    shortdesc = StringCol(dbName='shortdesc', notNull=True, default=""),
    description = StringCol(dbName='description', notNull=True),
    build = ForeignKey(dbName='build', foreignKey='Build',
                   notNull=True),
    binpackageformat = IntCol(dbName='binpackageformat', notNull=True),
    component = ForeignKey(dbName='component',
                   foreignKey='Component', notNull=True),
    section = ForeignKey(dbName='section', foreignKey='Section',
                   notNull=True),
    priority = IntCol(dbName='priority'),
    shlibdeps = StringCol(dbName='shlibdeps'),
    depends = StringCol(dbName='depends'),
    recommends = StringCol(dbName='recommends'),
    suggests = StringCol(dbName='suggests'),
    conflicts = StringCol(dbName='conflicts'),
    replaces = StringCol(dbName='replaces'),
    provides = StringCol(dbName='provides'),
    essential = BoolCol(dbName='essential'),
    installedsize = IntCol(dbName='installedsize'),
    copyright = StringCol(dbName='copyright'),
    licence = StringCol(dbName='licence'),

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
            'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id'
            ' AND SourcePackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackagePublishing.status = %d'
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


class BinaryPackageName(SQLBase):
    _table = 'BinaryPackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
    ]

    # Got from BinaryPackageName class
    binarypackages = MultipleJoin(
            'BinaryPackage', joinColumn='binarypackagename'
            )
    ####

