# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, MultipleJoin

# launchpad imports
from canonical.database.sqlbase import SQLBase, quote
from canonical.lp.dbschema import EnumCol, PackagePublishingStatus, \
        SourcePackageFormat

# launchpad interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageInDistro
from canonical.launchpad.interfaces import ISourcePackageInDistroSet, \
     ISourcePackageSet
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
     VSourcePackageReleasePublishing

class SourcePackageInDistro(SQLBase):
    """
    Represents source releases published in the specified distribution. This
    view's contents are uniqued, for the following reason: a certain package
    can have multiple releases in a certain distribution release.
    """

    implements(ISourcePackageInDistro)

    _table = 'VSourcePackageInDistro'
   
    #
    # Columns
    #
    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest')

    format = EnumCol(dbName='format',
                     schema=SourcePackageFormat,
                     default=SourcePackageFormat.DPKG,
                     notNull=True)

    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)
    #maintainer = ForeignKey(foreignKey='Person', dbName='maintainer',
    #                        notNull=True)
    name = StringCol(dbName='name', notNull=True)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')


class SourcePackageInDistroSet(object):
    """A Set of SourcePackages in a given DistroRelease"""
    implements(ISourcePackageInDistroSet)
    def __init__(self, distrorelease):
        """Take the distrorelease when it makes part of the context"""
        self.distrorelease = distrorelease
        self.title = 'Source Packages in: ' + distrorelease.title

    def findPackagesByName(self, pattern):
        srcutil = getUtility(ISourcePackageSet)
        return srcutil.findByNameInDistroRelease(self.distrorelease.id,
                                                 pattern)

    def __iter__(self):
        query = ('distrorelease = %d'
                 % (self.distrorelease.id))
        return iter(SourcePackageInDistro.select(query,
                        orderBy='VSourcePackageInDistro.name',
                        distinct=True))

    def __getitem__(self, name):
        publishing_status = PackagePublishingStatus.PUBLISHED.value

        query = ('distrorelease = %d AND publishingstatus=%d AND name=%s'
                 % (self.distrorelease.id, publishing_status, quote(name)))

        try:
            return VSourcePackageReleasePublishing.select(query)[0]
        except IndexError:
            raise KeyError, name

