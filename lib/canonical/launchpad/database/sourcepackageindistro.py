# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, MultipleJoin

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageInDistro
from canonical.launchpad.database.sourcepackage import SourcePackage
    
#
#
#

class SourcePackageInDistro(SourcePackage):
    implements(ISourcePackageInDistro)
    """
    Represents source packages that have releases published in the
    specified distribution. This view's contents are uniqued, for the
    following reason: a certain package can have multiple releases in a
    certain distribution release.
    """
    _table = 'VSourcePackageInDistro'
   
    #
    # Columns
    #
    name = StringCol(dbName='name', notNull=True)

    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')

    releases = MultipleJoin('SourcePackageRelease', joinColumn='sourcepackage')


