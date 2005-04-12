# Python imports
import os
from sets import Set
from urllib2 import URLError

# Zope imports
from zope.interface import implements
from zope.app import zapi

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, MultipleJoin, DateTimeCol

from canonical.database.sqlbase import SQLBase
from canonical.lp.dbschema import EnumCol, SourcePackageUrgency, \
        SourcePackageFormat

# interfaces and database 
from canonical.launchpad.interfaces import \
        ISourcePackageRelease, ISourcePackageReleaseSet

from canonical.launchpad.database.binarypackage import BinaryPackage, \
    DownloadURL

from canonical.librarian.interfaces import ILibrarianClient

class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(foreignKey='Person', dbName='creator', notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
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
    format = EnumCol(dbName='format',
                     schema=SourcePackageFormat,
                     default=SourcePackageFormat.DPKG,
                     notNull=True)
    uploaddistrorelease = ForeignKey(foreignKey='DistroRelease',
                                     dbName='uploaddistrorelease')
    # Joins
    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease')
    files = MultipleJoin('SourcePackageReleaseFile',
                         joinColumn='sourcepackagerelease')

    # Properties
    def name(self):
        return self.sourcepackagename.name
    name = property(name)

    def binaries(self):
        clauseTables = ('SourcePackageRelease', 'BinaryPackage', 'Build')

        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i' % self.id)

        return BinaryPackage.select(query, clauseTables=clauseTables)
    binaries = property(binaries)

    def files_url(self):
        downloader = zapi.getUtility(ILibrarianClient)

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


class SourcePackageReleaseSet:

    implements(ISourcePackageReleaseSet)

    def getByCreatorID(self, personID):
        querystr = """sourcepackagerelease.creator = %d AND
                      sourcepackagerelease.sourcepackagename = 
                        sourcepackagename.id""" % personID
        return SourcePackageRelease.select(
            querystr,
            orderBy='SourcePackageName.name',
            clauseTables=['SourcePackageRelease', 'SourcePackageName'])


