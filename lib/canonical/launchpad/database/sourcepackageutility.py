# Zope imports
from zope.interface import implements

#launchpad imports
from canonical.database.sqlbase import quote

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageUtility
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
     VSourcePackageReleasePublishing

#
#
#

class SourcePackageUtility(object):
    """A utility for sourcepackages"""
    implements(ISourcePackageUtility)

    def findByNameInDistroRelease(self, distroreleaseID,
                                  pattern, fti=False):
        """Returns a set o sourcepackage that matchs pattern
        inside a distrorelease"""

        clauseTables = ()

        pattern = pattern.replace('%', '%%')

        if fti:
            clauseTables = ('SourcePackage',)
            query = ('VSourcePackageReleasePublishing.sourcepackage = '
                     'SourcePackage.id AND '
                     'distrorelease = %d AND '
                     '(name ILIKE %s OR SourcePackage.fti @@ ftq(%s))'
                     %(distroreleaseID,
                       quote('%%'+pattern+'%%'),
                       quote(pattern))
                     )

        else:
            query = ('distrorelease = %d AND '
                     'name ILIKE %s '
                     % (distroreleaseID, quote('%%'+pattern+'%%'))
                     )

        return VSourcePackageReleasePublishing.select(query, orderBy='name',
                                                      clauseTables=clauseTables)

    def getByNameInDistroRelease(self, distroreleaseID, name):
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

