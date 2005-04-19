# Zope imports
from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol

from canonical.database.sqlbase import quote
from canonical.database.datetimecol import UtcDateTimeCol

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageReleasePublishing, \
    IPOTemplateSet

from canonical.launchpad.database.sourcepackagerelease import \
     SourcePackageRelease

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import PackagePublishingStatus


class VSourcePackageReleasePublishing(SourcePackageRelease):
    """A SourcePackageRelease that is published in a distrorelease. Note
    that there are two distrorelease fields: uploaddistrorelease and
    distrorelease. The one you want is distrorelease which
    is the distrorelease into which this sourcepackagerelease is published.
    The other one is the original distrorelease into which this
    SourcePackageRelease was first uploaded in the Launchpad."""

    implements(ISourcePackageReleasePublishing)

    _table = 'VSourcePackageReleasePublishing'

    # XXXkiko: IDs in this table are *NOT* unique!
    # XXX sabdfl 24/03/05 why? sourcepackagerelease.id would be unique, I
    # think.
    
    # These are the EXTRA fields in VSourcePackageReleasePublishing that are
    # not in the underlying SourcePackageRelease
    name = StringCol(dbName='name')
    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer')
    publishingstatus = EnumCol(dbName='publishingstatus',
                               schema=PackagePublishingStatus)
    datepublished = UtcDateTimeCol(dbName='datepublished')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
    componentname = StringCol(dbName='componentname')
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename')

    def title(self):
        title = 'Source package '
        title += self.name
        title += ' in ' + self.distrorelease.distribution.name
        title += ' ' + self.distrorelease.name
        return title
    title = property(title)

    # XXX sabdfl 24/03/05 this is the hack of the century, please remove
    # asap
    def sourcepackage(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        return SourcePackage(sourcepackagename=self.sourcepackagename,
                             distrorelease=self.distrorelease)
    sourcepackage = property(sourcepackage)


# 24/03/05 sabdfl I've renamed this to XXXcreateSourcePackage because I
# don't think it's used any longer, please remove if it's still here in a
# few months.
def XXXcreateSourcePackage(name, maintainer=0):
    # FIXME: maintainer=0 is a hack.  It should be required (or the DB shouldn't
    #        have NOT NULL on that column).
    return SourcePackage(
        name=name, 
        maintainer=maintainer,
        title='', # FIXME
        description='', # FIXME
    )

