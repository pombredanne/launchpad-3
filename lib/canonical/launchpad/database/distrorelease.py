__metaclass__ = type

from sets import Set

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase
from canonical.lp import dbschema

# interfaces and database
from canonical.launchpad.interfaces import IDistroRelease, IPOTemplateSet, \
     IDistroReleaseSet

from canonical.launchpad.database import SourcePackageInDistro, \
    SourcePackageInDistroSet, PublishedPackageSet, PackagePublishing

from canonical.launchpad.database.distroarchrelease import DistroArchRelease

class DistroRelease(SQLBase):
    """A particular release of a distribution."""
    implements(IDistroRelease)

    _table = 'DistroRelease'
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=True)
    bugtasks = MultipleJoin('BugTask', joinColumn='distrorelease')
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    shortdesc = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    components = ForeignKey(
        dbName='components', foreignKey='Schema', notNull=True)
    sections = ForeignKey(
        dbName='sections', foreignKey='Schema', notNull=True)
    releasestate = IntCol(notNull=True)
    datereleased = DateTimeCol(notNull=True)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    lucilleconfig = StringCol(notNull=False)
    architectures = MultipleJoin('DistroArchRelease',
            joinColumn='distrorelease')

    def parent(self):
        if self.parentrelease:
            return self.parentrelease.title
        return ''
    parent = property(parent)

    def state(self):
        return self._getState(self.releasestate)
    state = property(state)

    def sourcecount(self):
        # Import inside method to avoid circular import
        # See the top of the file
        from canonical.launchpad.database import SourcePackagePublishing
        query = ('SourcePackagePublishing.status = %s '
                 'AND SourcePackagePublishing.distrorelease = %s'
                 % (dbschema.PackagePublishingStatus.PUBLISHED.value,
                    self.id))
        return SourcePackagePublishing.select(query).count()
    sourcecount = property(sourcecount)

    def binarycount(self):
        clauseTables = ('DistroArchRelease',)
        query = ('PackagePublishing.status = %s '
                 'AND PackagePublishing.distroarchrelease = '
                 'DistroArchRelease.id '
                 'AND DistroArchRelease.distrorelease = %s'
                 % (dbschema.PackagePublishingStatus.PUBLISHED.value,
                    self.id))
        return PackagePublishing.select(
            query, clauseTables=clauseTables).count()
    binarycount = property(binarycount)

    def bugCounter(self):
        counts = []

        clauseTables = ("VSourcePackageInDistro",
                        "SourcePackage")
        severities = [
            dbschema.BugTaskStatus.NEW,
            dbschema.BugTaskStatus.ACCEPTED,
            dbschema.BugTaskStatus.FIXED,
            dbschema.BugTaskStatus.REJECTED
        ]

        _query = ("bugtask.distrorelease = %i AND "
                  "bugtask.bugstatus = %i"
                 )

        for severity in severities:
            query = _query %(self.id, int(severity))
            count = BugTask.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        counts.insert(0, sum(counts))
        return counts
    bugCounter = property(bugCounter)

    def _getState(self, value):
        for status in dbschema.DistributionReleaseState.items:
            if status.value == value:
                return status.title
        return 'Unknown'

    def architecturecount(self):
        return len(list(self.architectures))

    def getBugSourcePackages(self):
        """Get SourcePackages in a DistroRelease with BugTask"""

        clauseTables=["BugTask",]
        query = ("VSourcePackageInDistro.distrorelease = %i AND "
                 "VSourcePackageInDistro.distro = BugTask.distribution AND "
                 "VSourcePackageInDistro.name = BugTask.sourcepackagename AND "
                 "(BugTask.status != %i OR BugTask.status != %i)"
                 %(self.id,
                   dbschema.BugTaskStatus.FIXED,
                   dbschema.BugTaskStatus.REJECTED))

        return SourcePackageInDistro.select(
            query, clauseTables=clauseTables, distinct=True)

    def findSourcesByName(self, pattern):
        srcset = getUtility(ISourcePackageSet)
        return srcset.findByNameInDistroRelease(self.id, pattern)

    def traverse(self, name):
        if name == '+sources':
            return SourcePackageInDistroSet(self)
        elif name  == '+packages':
            return PublishedPackageSet()
        elif name == '+rosetta':
            potemplateset = getUtility(IPOTemplateSet)
            return potemplateset.getSubset(distrorelease=self)
        else:
            return self.__getitem__(name)

    def __getitem__(self, arch):
        try:
            return DistroArchRelease.selectBy(distroreleaseID=self.id,
                                              architecturetag=arch)[0]
        except:
            raise KeyError, 'Unknown architecture %s for %s %s' % (
                      arch,
                      self.distribution.name,
                      self.name )


class DistroReleaseSet:
    implements(IDistroReleaseSet)

    def get(self, distroreleaseid):
        """See canonical.launchpad.interfaces.IDistroReleaseSet."""
        return DistroRelease.get(distroreleaseid)
