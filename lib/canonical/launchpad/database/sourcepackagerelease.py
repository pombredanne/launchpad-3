# Python imports
import os
from sets import Set
from urllib2 import URLError

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, DateTimeCol

from canonical.librarian.client import FileDownloadClient
from canonical.database.sqlbase import SQLBase
from canonical.lp.dbschema import EnumCol, SourcePackageUrgency

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageRelease

from canonical.launchpad.database.binarypackage import BinaryPackage, \
    DownloadURL

#
#
#

class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(foreignKey='Person', dbName='creator', notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackage = ForeignKey(foreignKey='SourcePackage',
                               dbName='sourcepackage', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)
    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer',
                            notNull=True)
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')
    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest')

    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
                      notNull=True)
    dateuploaded = DateTimeCol(dbName='dateuploaded', notNull=True,
                               default='NOW')

    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = StringCol(dbName='changelog')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    architecturehintlist = StringCol(dbName='architecturehintlist')

    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease')

    files = MultipleJoin('SourcePackageReleaseFile',
                         joinColumn='sourcepackagerelease')
    #
    # Properties
    #
    def _name(self):
        return self.sourcepackage.sourcepackagename.name
    name = property(_name)

    def binaries(self):
        clauseTables = ('SourcePackageRelease', 'BinaryPackage', 'Build')

        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i' % self.id)

        return BinaryPackage.select(query, clauseTables=clauseTables)
    binaries = property(binaries)

    def files_url(self):
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


