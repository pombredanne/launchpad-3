# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound, \
    StringCol, ForeignKey, MultipleJoin, BoolCol, DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.launchpad.database.bug import BugTask
from canonical.launchpad.database.publishedpackage import PublishedPackageSet
from canonical.launchpad.database.distrorelease import DistroRelease
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.lp.dbschema import BugTaskStatus, DistributionReleaseStatus
from canonical.launchpad.interfaces import IDistribution, IDistributionSet, \
    IDistroPackageFinder, ITeamMembershipSubset, ITeam

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
    members = ForeignKey(dbName='members', foreignKey='Person', notNull=True)
    releases = MultipleJoin('DistroRelease', joinColumn='distribution')
    bounties = RelatedJoin(
        'Bounty', joinColumn='distribution', otherColumn='bounty',
        intermediateTable='DistroBounty')
    bugtasks = MultipleJoin('BugTask', joinColumn='distribution')

    def currentrelease(self):
        for rel in self.releases:
            if rel.releasestatus in [
                DistributionReleaseStatus.DEVELOPMENT,
                DistributionReleaseStatus.FROZEN ]:
                return rel
        return None
    currentrelease = property(currentrelease)

    def memberslist(self):
        if not ITeam.providedBy(self.members):
            return
        return ITeamMembershipSubset(self.members).getActiveMemberships()

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

        clauseTables = ["VSourcePackageInDistro"]
        severities = [
            BugTaskStatus.NEW,
            BugTaskStatus.ACCEPTED,
            BugTaskStatus.REJECTED,
            BugTaskStatus.FIXED]

        query = ("bugtask.distribution = %s AND "
                 "bugtask.bugstatus = %i")

        for severity in severities:
            query = query %(quote(self.id), severity)
            count = BugTask.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        return counts

    def getRelease(self, name_or_version):
        """See IDistribution."""
        try:
            return DistroRelease.selectBy(distributionID=self.id,
                                          name=name_or_version)[0]
        except IndexError:
            try:
                return DistroRelease.selectBy(distributionID=self.id,
                                              version=name_or_version)[0]
            except IndexError:
                raise NotFoundError

    bugCounter = property(bugCounter)

    def getDevelopmentReleases(self):
        """See IDistribution."""
        return DistroRelease.selectBy(
            distributionID = self.id,
            releasestatus = DistributionReleaseStatus.DEVELOPMENT )

    def getSourcePackage(self, name):
        """See IDistribution."""
        return SourcePackage(name, self.currentrelease)

class DistributionSet:
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


class DistroPackageFinder:

    implements(IDistroPackageFinder)

    def __init__(self, distribution=None, processorfamily=None):
        self.distribution = distribution
