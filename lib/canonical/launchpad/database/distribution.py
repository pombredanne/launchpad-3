# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.launchpad.database.bug import BugTask
from canonical.launchpad.database.publishedpackage import PublishedPackageSet
from canonical.lp import dbschema

# interfaces and database
from canonical.launchpad.interfaces import IDistribution
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.interfaces import IDistroPackageFinder

__all__ = ['Distribution', 'DistributionSet']


class Distribution(SQLBase):
    """A distribution of an operating system, e.g. Debian GNU/Linux."""
    implements(IDistribution)

    _defaultOrder='name'

    name = StringCol(notNull=True, alternateID=True, unique=True)
    displayname = StringCol()
    title = StringCol()
    summary = StringCol()
    description = StringCol()
    domainname = StringCol()
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    releases = MultipleJoin('DistroRelease', joinColumn='distribution')
    bounties = RelatedJoin(
        'Bounty', joinColumn='project', otherColumn='bounty',
        intermediateTable='ProjectBounty')
    bugtasks = MultipleJoin('BugTask', joinColumn='distribution')
    role_users = MultipleJoin('DistributionRole', joinColumn='distribution')

    def traverse(self, name):
        if name == '+packages':
            return PublishedPackageSet()
        return self.__getitem__(name)

    def __getitem__(self, name):
        for release in self.releases:
            if release.name == name:
                return release
        raise KeyError, name

    def __iter__(self):
        return iter(self.releases)

    def bugCounter(self):
        counts = []

        clauseTables = ("VSourcePackageInDistro",
                        "SourcePackage")
        severities = [
            dbschema.BugTaskStatus.NEW,
            dbschema.BugTaskStatus.ACCEPTED,
            dbschema.BugTaskStatus.REJECTED,
            dbschema.BugTaskStatus.FIXED]

        query = ("bugtask.distribution = %s AND "
                 "bugtask.bugstatus = %i")

        for severity in severities:
            query = query %(quote(self.id), severity)
            count = BugTask.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        return counts
    bugCounter = property(bugCounter)


class DistributionSet(object):
    """This class is to deal with Distribution related stuff"""

    implements(IDistributionSet)

    def __init__(self):
        self.title = "Launchpad Distributions"

    def __iter__(self):
        return iter(Distribution.select())

    def __getitem__(self, name):
        try:
            return Distribution.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def get(self, distributionid):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        return Distribution.get(distributionid)

    def count(self):
        return Distribution.select().count()

    def getDistros(self):
        """Returns all Distributions available on the database"""
        return Distribution.select()

    def getDistribution(self, name):
        """Returns a Distribution with name = name"""
        return self[name]

class DistroPackageFinder(object):

    implements(IDistroPackageFinder)

    def __init__(self, distribution=None, processorfamily=None):
        self.distribution = distribution
        # find the x86 processorfamily
