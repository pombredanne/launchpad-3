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
# The import is done inside BinaryPackage.maintainer to avoid circular import
##from canonical.launchpad.database.sourcepackage import SourcePackageRelease

class BinaryPackage(SQLBase):
    implements(IBinaryPackage)
    _table = 'BinaryPackage'
    binarypackagename = ForeignKey(dbName='binarypackagename', 
                   foreignKey='BinaryPackageName', notNull=True)
    version = StringCol(dbName='version', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True, default="")
    description = StringCol(dbName='description', notNull=True)
    build = ForeignKey(dbName='build', foreignKey='Build',
                   notNull=True)
    binpackageformat = IntCol(dbName='binpackageformat', notNull=True)
    component = ForeignKey(dbName='component',
                   foreignKey='Component', notNull=True)
    section = ForeignKey(dbName='section', foreignKey='Section',
                   notNull=True)
    priority = IntCol(dbName='priority')
    shlibdeps = StringCol(dbName='shlibdeps')
    depends = StringCol(dbName='depends')
    recommends = StringCol(dbName='recommends')
    suggests = StringCol(dbName='suggests')
    conflicts = StringCol(dbName='conflicts')
    replaces = StringCol(dbName='replaces')
    provides = StringCol(dbName='provides')
    essential = BoolCol(dbName='essential')
    installedsize = IntCol(dbName='installedsize')
    copyright = StringCol(dbName='copyright')
    licence = StringCol(dbName='licence')

    def _title(self):
        return '%s-%s' % (self.binarypackagename.name, self.version)
    title = property(_title, None)


    def name(self):
        return self.binarypackagename.name
    name = property(name)

    def maintainer(self):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.sourcepackage import \
             SourcePackageRelease

        return self.sourcepackagerelease.sourcepackage.maintainer
    maintainer = property(maintainer)

    def current(self, distroRelease):
        """Currently published releases of this package for a given distro.
        
        :returns: iterable of SourcePackageReleases
        """
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.sourcepackage import \
             SourcePackageRelease

        return self.build.sourcepackagerelease.sourcepackage.current(distroRelease)

    def lastversions(self, distroRelease):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.sourcepackage import \
             SourcePackageRelease

        last = list(SourcePackageRelease.select(
            'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id'
            ' AND SourcePackagePublishing.distrorelease = %d'
            ' AND SourcePackageRelease.sourcepackage = %d'
            ' AND SourcePackagePublishing.status = %d'
            ' ORDER BY sourcePackageRelease.dateuploaded DESC'
            % (distroRelease.id,
               self.build.sourcepackagerelease.sourcepackage.id,
               dbschema.PackagePublishingStatus.SUPERCEDED)
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

    #
    # BinaryPackage Class Methods
    #

    def findBinariesByName(klass, distrorelease, pattern):
        pattern = pattern.replace('%', '%%')

        query = (
        'PackagePublishing.binarypackage = BinaryPackage.id AND '
        'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        'DistroArchRelease.distrorelease = %d AND '
        'BinaryPackage.binarypackagename = BinaryPackageName.id '
        'AND (BinaryPackageName.name ILIKE %s '
        'OR BinaryPackage.shortdesc ILIKE %s)'
        %(distrorelease.id,
          quote('%%' + pattern + '%%'),
          quote('%%' + pattern + '%%'))
        )

        # FIXME: (SQLObject_Selection+batching) Daniel Debonzi - 2004-10-13
        # The selection is limited here because batching and SQLObject
        # selection still not working properly. Now the days for each
        # page showing BATCH_SIZE results the SQLObject makes queries
        # for all the related things available on the database which
        # presents a very slow result.
        # Is those unique ?
        return klass.select(query,
                            orderBy='BinaryPackageName.name')[:500]
    findBinariesByName = classmethod(findBinariesByName)

    def getBinariesByName(klass, distrorelease, name):

        query = (
            'PackagePublishing.binarypackage = BinaryPackage.id AND '
            'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
            'DistroArchRelease.distrorelease = %d AND '
            'BinaryPackage.binarypackagename = BinaryPackageName.id '
            'AND BinaryPackageName.name = %s '
            %(distrorelease.id, quote(name))
            )
        return klass.select(query)
    getBinariesByName = classmethod(getBinariesByName)
    
    def getBinaries(klass, distrorelease):
        query = ('PackagePublishing.binarypackage = BinaryPackage.id AND '
                 'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
                 'DistroArchRelease.distrorelease = %d '
                 % distrorelease.id
                 )

        # FIXME: (distinct_query) Daniel Debonzi 2004-10-13
        # FIXME: (SQLObject_Selection+batching)
        # they were LIMITED by hand
        return klass.select(query, orderBy=\
                            'BinaryPackageName.name')[:500]

    getBinaries = classmethod(getBinaries)
        
    def getByVersion(klass, binarypackages, version):
        """From get given BinaryPackageSelection get the one with version"""

        query = binarypackages.clause + \
                ' AND BinaryPackage.version = %s' %quote(version)
        return klass.select(query)

    getByVersion = classmethod(getByVersion)

    def selectByArchtag(klass, binarypackages, archtag):
        """Select from a give BinaryPackage.SelectResult BinaryPackage with archtag"""
        query = binarypackages.clause + \
                ' AND DistroArchRelease.architecturetag = %s' %quote(archtag)
        return klass.select(query)[0]
        
    selectByArchtag = classmethod(selectByArchtag)


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


