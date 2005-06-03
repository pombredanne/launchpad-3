# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackage', 'BinaryPackageSet', 'DownloadURL']

from urllib2 import URLError

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol

from canonical.librarian.interfaces import ILibrarianClient
from canonical.database.sqlbase import SQLBase, quote, sqlvalues, quote_like

from canonical.launchpad.interfaces import IBinaryPackage, IDownloadURL
from canonical.launchpad.interfaces import IBinaryPackageSet
from canonical.launchpad.database.publishing import PackagePublishing

from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol


class BinaryPackage(SQLBase):
    implements(IBinaryPackage)
    _table = 'BinaryPackage'
    binarypackagename = ForeignKey(dbName='binarypackagename', 
                                 foreignKey='BinaryPackageName', notNull=True)
    version = StringCol(dbName='version', notNull=True)
    summary = StringCol(dbName='summary', notNull=True, default="")
    description = StringCol(dbName='description', notNull=True)
    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    binpackageformat = EnumCol(dbName='binpackageformat', notNull=True,
                               schema=dbschema.BinaryPackageFormat)
    component = ForeignKey(dbName='component', foreignKey='Component',
                           notNull=True)
    section = ForeignKey(dbName='section', foreignKey='Section', notNull=True)
    priority = EnumCol(dbName='priority',
                       schema=dbschema.BinaryPackagePriority)
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

    def title(self):
        return '%s-%s' % (self.binarypackagename.name, self.version)
    title = property(title, None)


    def name(self):
        return self.binarypackagename.name
    name = property(name)

    def maintainer(self):
        return self.sourcepackagerelease.sourcepackage.maintainer
    maintainer = property(maintainer)

    def current(self, distroRelease):
        """Return currently published releases of this package for a given
        distro.

        :returns: iterable of SourcePackageReleases
        """
        return self.build.sourcepackagerelease.sourcepackage.current(
            distroRelease)

    def lastversions(self):
        """Return the SUPERSEDED BinaryPackages in a DistroRelease
        that comes from the same SourcePackage.
        """
        # Daniel Debonzi: To get the lastest versions of a BinaryPackage
        # Im suposing that one BinaryPackage is build for only one
        # DistroRelease (Each DistroRelease compile all its Packages). 
        # (BinaryPackage.build.distroarchrelease = \
        # PackagePublishing.distroarchrelease
        # where PackagePublishing.binarypackage = BinaryPackage.id)
        # When it is not true anymore, probably it should
        # be retrieved in a view class where I can use informations from
        # the launchbag.

        clauseTables = ['PackagePublishing', 'BinaryPackageName']
        query = ('PackagePublishing.binarypackage = BinaryPackage.id '
                 'AND BinaryPackage.binarypackagename = BinaryPackageName.id '
                 'AND BinaryPackageName.id = %s '
                 'AND PackagePublishing.distroarchrelease = %s '
                 'AND PackagePublishing.status = %s'
                 % sqlvalues(self.binarypackagename.id,
                             self.build.distroarchrelease.id,
                             dbschema.PackagePublishingStatus.SUPERSEDED)
                 )

        return list(BinaryPackage.select(
            query, clauseTables=clauseTables, distinct=True))

    def status(self):
        """Returns the BinaryPackage Status."""
        # Daniel Debonzi: To get the lastest versions of a BinaryPackage
        # Im suposing that one BinaryPackage is build for only one
        # DistroRelease. If it will happen to have a BinaryPackage
        # Builded for one DistroRelease included in other DistroReleases
        # It might be reviewed
        packagepublishing = PackagePublishing.selectOneBy(
            binarypackageID=self.id,
            distroarchreleaseID=self.build.distroarchrelease.id)
        if packagepublishing is None:
            raise KeyError('BinaryPackage not found in PackagePublishing')
        return packagepublishing.status.title
    status = property(status)

    def files_url(self):
        """Return an URL to Download this Package."""
        downloader = getUtility(ILibrarianClient)

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
        clauseTables = ["Build"]
        query = """Build.id = build
                   AND  Build.distroarchrelease = %d
                   AND  binarypackagename = %d
                   AND  version = %s""" % sqlvalues(
                       self.build.distroarchrelease.id,
                       self.binarypackagename.id,
                       version)
        item = BinaryPackage.selectOne(query, clauseTables=clauseTables)
        if item is None:
            raise KeyError("Version Not Found", version)
        return item


class BinaryPackageSet:
    """A Set of BinaryPackages."""
    implements(IBinaryPackageSet)

    def findByNameInDistroRelease(self, distroreleaseID, pattern, archtag=None,
                                  fti=False):
        """Returns a set o binarypackages that matchs pattern inside a
        distrorelease.
        """
        pattern = pattern.replace('%', '%%')

        clauseTables = ['PackagePublishing', 'DistroArchRelease',
                        'BinaryPackage', 'BinaryPackageName']

        query = (
            'PackagePublishing.binarypackage = BinaryPackage.id AND '
            'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
            'DistroArchRelease.distrorelease = %d AND '
            'BinaryPackage.binarypackagename = BinaryPackageName.id '
            % distroreleaseID
            )

        if fti:
            query += """
                AND (BinaryPackageName.name
                    LIKE lower('%%' || %s || '%%')
                OR BinaryPackage.fti @@ ftq(%s))
                """ % (quote_like(pattern), quote(pattern))
        else:
            query += ('AND BinaryPackageName.name ILIKE %s '
                      % sqlvalues('%%' + pattern + '%%')
                      )

        if archtag:
            query += ('AND DistroArchRelease.architecturetag=%s'
                      % sqlvalues(archtag))

        return BinaryPackage.select(query, clauseTables=clauseTables,
                                    orderBy='BinaryPackageName.name')

    def getByNameInDistroRelease(self, distroreleaseID, name=None,
                                 version=None, archtag=None, orderBy=None):
        """Get a BinaryPackage in a DistroRelease by its name."""

        clauseTables = ['PackagePublishing', 'DistroArchRelease',
                        'BinaryPackage', 'BinaryPackageName']

        query = (
            'PackagePublishing.binarypackage = BinaryPackage.id AND '
            'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
            'DistroArchRelease.distrorelease = %d AND '
            'BinaryPackage.binarypackagename = BinaryPackageName.id '
            % distroreleaseID
            )

        if name:
            query += 'AND BinaryPackageName.name = %s '% sqlvalues(name)

        # Look for a specific binarypackage version or if version == None
        # return the current one
        if version:
            query += ('AND BinaryPackage.version = %s '
                      % sqlvalues(version))
        else:
            query += ('AND PackagePublishing.status = %s '
                      % sqlvalues(dbschema.PackagePublishingStatus.PUBLISHED))

        if archtag:
            query += ('AND DistroArchRelease.architecturetag = %s '
                      % sqlvalues(archtag))

        return BinaryPackage.select(query, distinct=True,
                                    clauseTables=clauseTables,
                                    orderBy=orderBy)

    # Used outside

    def getDistroReleasePackages(self, distroreleaseID):
        """Get a set of BinaryPackages in a distrorelease"""
        clauseTables = ['PackagePublishing', 'DistroArchRelease',
                        'BinaryPackageName']

        query = ('PackagePublishing.binarypackage = BinaryPackage.id AND '
                 'PackagePublishing.distroarchrelease = '
                 'DistroArchRelease.id AND '
                 'DistroArchRelease.distrorelease = %d AND '
                 'BinaryPackage.binarypackagename = BinaryPackageName.id'
                 % distroreleaseID
                 )

        return BinaryPackage.select(query,clauseTables=clauseTables,
                                    orderBy='BinaryPackageName.name')

    def getByNameVersion(self, distroreleaseID, name, version):
        """Get a set of  BinaryPackages in a DistroRelease by its name and
        version.
        """
        return self.getByName(distroreleaseID, name, version)

    def getByArchtag(self, distroreleaseID, name, version, archtag):
        """Get a BinaryPackage in a DistroRelease by its name, version and
        archtag.
        """
        return self.getByName(distroreleaseID, name, version, archtag)[0]

    def getBySourceName(self, DistroRelease, sourcepackagename):
        """Get a set of BinaryPackage generated by the current
        SourcePackageRelease with an SourcePackageName inside a
        DistroRelease context.
        """
        clauseTables = ['SourcePackageName', 'SourcePackageRelease',
                        'SourcePackagePublishing', 'Build']

        query = ('SourcePackageRelease.sourcepackagename = '
                 'SourcePackageName.id AND '
                 'SourcePackagePublishing.sourcepackagerelease = '
                 'SourcePackageRelease.id AND '
                 'Build.sourcepackagerelease = SourcePackageRelease.id AND '
                 'BinaryPackage.build = Build.id AND '
                 'SourcePackageName.name = %s AND '
                 'SourcePackagePublishing.distrorelease = %s AND '
                 'SourcePackagePublishing.status = %s'
                 % sqlvalues(sourcepackagename,
                             DistroRelease.id,
                             dbschema.PackagePublishingStatus.PUBLISHED
                             )
                 )
        raise RuntimeError("Needs fixing by debonzi")
        return BinaryPackage.select(query, clauseTables=clauseTables)

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if (name is None and distribution is None and
            distrorelease is None and text is None):
            raise ValueError('must give something to the query.')
        clauseTables = Set(['BinaryPackage'])
        # XXX sabdfl this is not yet done 12/12/04
        # XXX What is not yet done?  Raise a NotImplementedError.
        raise NotImplementedError


class DownloadURL:
    implements(IDownloadURL)

    def __init__(self, filename, fileurl):
        self.filename = filename
        self.fileurl = fileurl

