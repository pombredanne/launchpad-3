# Zope imports
from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol

from canonical.database.sqlbase import quote

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageReleasePublishing, \
    IPOTemplateSet

from canonical.launchpad.database.sourcepackagerelease import \
     SourcePackageRelease
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import PackagePublishingStatus

#
#
#

class VSourcePackageReleasePublishing(SourcePackageRelease):
    implements(ISourcePackageReleasePublishing)
    _table = 'VSourcePackageReleasePublishing'

    # XXXkiko: IDs in this table are *NOT* unique!
    name = StringCol(dbName='name')
    shortdesc = StringCol(dbName='shortdesc')
    #maintainer = ForeignKey(foreignKey='Person', dbName='maintainer')
    description = StringCol(dbName='description')
    publishingstatus = EnumCol(dbName='publishingstatus',
                               schema=PackagePublishingStatus)
    datepublished = DateTimeCol(dbName='datepublished')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    componentname = StringCol(dbName='componentname')


    # XXX: Daniel Debonzi. Hack to do not query the sourcepackagename
    # inherited from SourcePackageRelease but that is not available in
    # VSourcePackageReleasePublishing
    sourcepackagename = None

    def _title(self):
        title = 'Source package '
        title += self.name
        title += ' in ' + self.distrorelease.distribution.name
        title += ' ' + self.distrorelease.name
        return title
    title = property(_title)

    def __getitem__(self, version):
        """Get a  SourcePackageRelease"""
        results = VSourcePackageReleasePublishing.select(
            "sourcepackage = %d AND version = %s"
            % (self.sourcepackage.id, quote(version)))
        if results.count() == 0:
            raise NotFoundError, version
        else:
            return results[0]

    def traverse(self, name):
        """See ISourcePackageReleasePublishing."""
        if name == '+rosetta':
            potemplateset = getUtility(IPOTemplateSet)
            return potemplateset.getSubset(
                distrorelease=self.distrorelease,
                sourcepackagename=self.sourcepackage.sourcepackagename)
        else:
            return self[name]


def createSourcePackage(name, maintainer=0):
    # FIXME: maintainer=0 is a hack.  It should be required (or the DB shouldn't
    #        have NOT NULL on that column).
    return SourcePackage(
        name=name, 
        maintainer=maintainer,
        title='', # FIXME
        description='', # FIXME
    )
