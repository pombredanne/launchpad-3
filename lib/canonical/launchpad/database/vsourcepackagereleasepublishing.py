# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, DateTimeCol

from canonical.database.sqlbase import quote

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageReleasePublishing, \
    IPOTemplateSet

from canonical.launchpad.database.sourcepackagerelease import \
     SourcePackageRelease

#
#
#

class VSourcePackageReleasePublishing(SourcePackageRelease):
    implements(ISourcePackageReleasePublishing)
    _table = 'VSourcePackageReleasePublishing'

    # XXXkiko: IDs in this table are *NOT* unique!
    name = StringCol(dbName='name')
    shortdesc = StringCol(dbName='shortdesc')
    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer')
    description = StringCol(dbName='description')
    publishingstatus = IntCol(dbName='publishingstatus')
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
        table = VSourcePackageReleasePublishing 
        try:            
            return table.select("sourcepackage = %d AND version = %s"
                                % (self.sourcepackage.id, quote(version)))[0]
        except IndexError:
            raise KeyError, 'Version Not Found'

    def traverse(self, name):
        """See ISourcePackageReleasePublishing."""
        if name == '+rosetta':
            pts = getUtility(IPOTemplateSet)
            return pts.distrorelease_sourcepackagename_subset(
                self.distrorelease, self.sourcepackage.sourcepackagename)
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
