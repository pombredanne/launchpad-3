
from sets import Set

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackage, \
                                           IBinaryPackageUtility, \
                                           ISourcePackageUtility, \
                                           IBinaryPackageName,\
                                           IBinaryPackageNameSet
from canonical.launchpad.database.publishing import PackagePublishing

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

    def lastversions(self):
        """Return the SUPERCEDED BinaryPackages in a DistroRelease
           that comes from the same SourcePackage"""

        clauseTable = ('PackagePublishing', 'BinaryPackageName',)
        query = ('PackagePublishing.binarypackage = BinaryPackage.id '
                 'AND BinaryPackage.binarypackagename = BinaryPackageName.id '
                 'AND BinaryPackageName.id = %d '
                 'AND PackagePublishing.distroarchrelease = %d '
                 'AND PackagePublishing.status = %d'
                 %(self.binarypackagename.id,
                   self.build.distroarchrelease.id,
                   dbschema.PackagePublishingStatus.SUPERCEDED,
                   ))

        return list(BinaryPackage.select(query,
                                         clauseTables=clauseTable,
                                         distinct=True))
                    
    def _priority(self):
        for priority in dbschema.BinaryPackagePriority.items:
            if priority.value == self.priority:
                return priority.title
        return 'Unknown (%d)' %self.priority

    pkgpriority = property(_priority)

    def _status(self):
        """Get the BinaryPackage Status"""

        try:
            packagepublishing = PackagePublishing.\
                                select('binarypackage=%d '
                                       'AND distroarchrelease=%d '
                                       %(self.id,
                                         self.build.distroarchrelease.id))[0];
        except IndexError:
            raise KeyError, 'BinaryPackage not found in PackagePublishing'
        
        try:
            return dbschema.PackagePublishingStatus.\
                   items[packagepublishing.status].title
        except KeyError:
            return 'Unknown'

    status = property(_status)

    def __getitem__(self, version):        
        clauseTables = ["Build",]        
        query = """Build.id = build
                   AND  Build.distroarchrelease = %d
                   AND  binarypackagename = %d
                   AND  version = %s""" % (self.build.distroarchrelease.id,
                                           self.binarypackagename.id,
                                           quote(version))
        try:
            return BinaryPackage.select(query, clauseTables=clauseTables)[0]
        except IndexError:
            raise KeyError, "Version Not Found"
        

class BinaryPackageSet(object):
    """A Set of BinaryPackages"""
    def __init__(self, distrorelease, arch):
        self.distrorelease = distrorelease
        self.arch = arch

    def findPackagesByName(self, pattern):
        """Search BinaryPackages matching pattern"""
        binset = getUtility(IBinaryPackageUtility)
        return binset.findByNameInDistroRelease(self.distrorelease.id, pattern)

    def __getitem__(self, name):
        binset = getUtility(IBinaryPackageUtility)
        try:
            return binset.getByNameInDistroRelease(self.distrorelease.id,
                                                   name=name,
                                                   archtag=self.arch)[0]
        except IndexError:
            raise KeyError
    
    def __iter__(self):
        binset = getUtility(IBinaryPackageUtility)
        return iter(binset.getByNameInDistroRelease(self.distrorelease.id,
                                                    archtag=self.arch))

class BinaryPackageUtility(object):
    """The set of BinaryPackage objects."""

    implements(IBinaryPackageUtility)

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if name is None and distribution is None and \
            distrorelease is None and text is None:
            raise NotImplementedError, 'must give something to the query.'
        clauseTables = Set(['BinaryPackage'])
        # XXX sabdfl this is not yet done 12/12/04

    def getByNameInDistroRelease(self, distroreleaseID, name=None,
                                 version=None, archtag=None):
        """Get an BinaryPackage in a DistroRelease by its name"""

        clauseTables = ('PackagePublishing', 'DistroArchRelease',
                        'BinaryPackage', 'BinaryPackageName')

        query = (
            'PackagePublishing.binarypackage = BinaryPackage.id AND '
            'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
            'DistroArchRelease.distrorelease = %d AND '
            'BinaryPackage.binarypackagename = BinaryPackageName.id '
            %(distroreleaseID)
            )

        if name:
            query += 'AND BinaryPackageName.name = %s '% (quote(name))

        # Look for a specific binarypackage version or if version == None
        # return the current one
        if version:
            query += ('AND BinaryPackage.version = %s '
                      %quote(version))
        else:
            query += ('AND PackagePublishing.status = %s'
                      % dbschema.PackagePublishingStatus.PUBLISHED)

        if archtag:
            query += ('AND DistroArchRelease.architecturetag = %s '
                      %quote(archtag))

        return BinaryPackage.select(query, distinct=True,
                                        clauseTables=clauseTables)

    def findByNameInDistroRelease(self, distroreleaseID, pattern):
        """Returns a set o binarypackages that matchs pattern
        inside a distrorelease"""

        pattern = pattern.replace('%', '%%')

        clauseTables = ('PackagePublishing', 'DistroArchRelease',
                        'BinaryPackage', 'BinaryPackageName')

        query = (
        'PackagePublishing.binarypackage = BinaryPackage.id AND '
        'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        'DistroArchRelease.distrorelease = %d AND '
        'BinaryPackage.binarypackagename = BinaryPackageName.id '
        'AND (BinaryPackageName.name ILIKE %s '
        'OR BinaryPackage.shortdesc ILIKE %s)'
        %(distroreleaseID,
          quote('%%' + pattern + '%%'),
          quote('%%' + pattern + '%%'))
        )

        return BinaryPackage.select(query,
                                    clauseTables=clauseTables,
                                    orderBy='BinaryPackageName.name')

    def getDistroReleasePackages(self, distroreleaseID):
        """Get a set of BinaryPackages in a distrorelease"""
        clauseTables = ('PackagePublishing', 'DistroArchRelease',
                        'BinaryPackageName')
        
        query = ('PackagePublishing.binarypackage = BinaryPackage.id AND '
                 'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
                 'DistroArchRelease.distrorelease = %d AND '
                 'BinaryPackage.binarypackagename = BinaryPackageName.id'
                 % distroreleaseID
                 )

        return BinaryPackage.select(query,clauseTables=clauseTables,
                                    orderBy='BinaryPackageName.name')
        
    def getByNameVersion(self, distroreleaseID, name, version):
        """Get a set of  BinaryPackages in a DistroRelease by its name and version"""
        return self.getByName(distroreleaseID, name, version)

    def getByArchtag(self, distroreleaseID, name, version, archtag):
        """Get a BinaryPackage in a DistroRelease by its name, version and archtag"""
        return self.getByName(distroreleaseID, name, version, archtag)[0]


class BinaryPackageName(SQLBase):

    implements(IBinaryPackageName)
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True)

    binarypackages = MultipleJoin(
            'BinaryPackage', joinColumn='binarypackagename'
            )

class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if name is None and distribution is None and \
            distrorelease is None and text is None:
            raise NotImplementedError, 'must give something to the query.'
        clauseTables = Set(['BinaryPackage'])
        # XXX sabdfl 12/12/04 not done yet

