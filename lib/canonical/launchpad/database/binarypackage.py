# Python imports
import os
from urllib2 import URLError

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol

from canonical.librarian.client import FileDownloadClient
from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackage, IDownloadURL
from canonical.launchpad.interfaces import IBinaryPackageUtility
from canonical.launchpad.interfaces import IBinaryPackageSet

from canonical.launchpad.database.publishing import PackagePublishing

#
#
#

class BinaryPackage(SQLBase):
    implements(IBinaryPackage)
    _table = 'BinaryPackage'
    binarypackagename = ForeignKey(dbName='binarypackagename', 
                                 foreignKey='BinaryPackageName', notNull=True)
    version = StringCol(dbName='version', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True, default="")
    description = StringCol(dbName='description', notNull=True)
    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    binpackageformat = IntCol(dbName='binpackageformat', notNull=True)
    component = ForeignKey(dbName='component', foreignKey='Component',
                           notNull=True)
    section = ForeignKey(dbName='section', foreignKey='Section', notNull=True)
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
    architecturespecific = BoolCol(dbName='architecturespecific')

    files = MultipleJoin('BinaryPackageFile',
                         joinColumn='binarypackage')

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
        return self.build.sourcepackagerelease.sourcepackage.current(\
                                                              distroRelease)

    def lastversions(self):
        """Return the SUPERSEDED BinaryPackages in a DistroRelease
           that comes from the same SourcePackage"""

        #
        # Daniel Debonzi: To get the lastest versions of a BinaryPackage
        # Im suposing that one BinaryPackage is build for only one
        # DistroRelease (Each DistroRelease compile all its Packages). 
        # (BinaryPackage.build.distroarchrelease = \
        # PackagePublishing.distroarchrelease
        # where PackagePublishing.binarypackage = BinaryPackage.id)
        # When it is not true anymore, probably it should
        # be retrieved in a view class where I can use informations from
        # the launchbag.
        #
        
        clauseTable = ('PackagePublishing', 'BinaryPackageName',)
        query = ('PackagePublishing.binarypackage = BinaryPackage.id '
                 'AND BinaryPackage.binarypackagename = BinaryPackageName.id '
                 'AND BinaryPackageName.id = %d '
                 'AND PackagePublishing.distroarchrelease = %d '
                 'AND PackagePublishing.status = %d'
                 %(self.binarypackagename.id,
                   self.build.distroarchrelease.id,
                   dbschema.PackagePublishingStatus.SUPERSEDED,
                   ))

        return list(BinaryPackage.select(query,
                                         clauseTables=clauseTable,
                                         distinct=True))

    #
    # Properties
    #
    
    def _priority(self):
        for priority in dbschema.BinaryPackagePriority.items:
            if priority.value == self.priority:
                return priority.title
        return 'Unknown (%d)' %self.priority

    pkgpriority = property(_priority)

    def _status(self):
        """Returns the BinaryPackage Status."""
        #
        # Daniel Debonzi: To get the lastest versions of a BinaryPackage
        # Im suposing that one BinaryPackage is build for only one
        # DistroRelease. If it will happen to have a BinaryPackage
        # Builded for one DistroRelease included in other DistroReleases
        # It might be reviewed
        #
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

    def files_url(self):
        """Return an URL to Download this Package"""
        # XXX: Daniel Debonzi 20050125
        # Get librarian host and librarian download port from
        # invironment variables until we have it configurable
        # somewhere.
        librarian_host = os.environ.get('LB_HOST', 'localhost')
        librarian_port = int(os.environ.get('LB_DPORT', '8000'))

        downloader = FileDownloadClient(librarian_host, librarian_port)

        urls = []

        for _file in self.files:
            try:
                url = downloader.getURLForAlias(_file.libraryfile.id)
            except URLError:
                # librarian not runnig or file not avaiable
                pass
            else:
                name = _file.libraryfile.filename
            
                urls.append(DownloadURL(name, url))

        return urls

    files_url = property(files_url)


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
    implements(IBinaryPackageSet)
    def __init__(self, distrorelease, arch):
        self.distrorelease = distrorelease
        self.arch = arch
        self.title = 'Packages in ' + distrorelease.name + ', ' +arch

    def findPackagesByName(self, pattern):
        """Search BinaryPackages matching pattern"""
        binset = getUtility(IBinaryPackageUtility)
        return binset.findByNameInDistroRelease(self.distrorelease.id, pattern)

    def findPackagesByArchtagName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageUtility)
        return binset.findByNameInDistroRelease(self.distrorelease.id,
                                                pattern, self.arch,
                                                fti)
        
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


class DownloadURL(object):
    implements(IDownloadURL)

    def __init__(self, filename, fileurl):
        self.filename = filename
        self.fileurl = fileurl
