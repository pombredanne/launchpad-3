# Python imports
from sets import Set

# Zope imports
from zope.interface import implements

from canonical.database.sqlbase import quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageUtility
from canonical.launchpad.database.binarypackage import BinaryPackage
#
#
#

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
            query += ('AND PackagePublishing.status = %s '
                      % dbschema.PackagePublishingStatus.PUBLISHED)

        if archtag:
            query += ('AND DistroArchRelease.architecturetag = %s '
                      %quote(archtag))

        return BinaryPackage.select(query, distinct=True,
                                        clauseTables=clauseTables)

    def findByNameInDistroRelease(self, distroreleaseID,
                                  pattern, archtag=None,
                                  fti=False):
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
        %distroreleaseID
        )

        if fti:
            query += ('AND (BinaryPackageName.name ILIKE %s '
                      'OR BinaryPackage.fti @@ ftq(%s))'
                      %(quote('%%' + pattern + '%%'),
                        quote(pattern))
        )
        else:
            query += ('AND BinaryPackageName.name ILIKE %s '
                      %quote('%%' + pattern + '%%')
                      )

        if archtag:
            query += ('AND DistroArchRelease.architecturetag=%s'
                      %quote(archtag))

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


