# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Distribution', 'DistributionSet', 'DistroPackageFinder']

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import (
    RelatedJoin, SQLObjectNotFound, StringCol, ForeignKey,
    MultipleJoin)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.distributionbounty import \
    DistributionBounty
from canonical.launchpad.database.distrorelease import DistroRelease
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.specification import Specification
from canonical.lp.dbschema import (EnumCol, BugTaskStatus,
    DistributionReleaseStatus, TranslationPermission)
from canonical.launchpad.interfaces import (IDistribution, IDistributionSet,
    IDistroPackageFinder)


class Distribution(SQLBase):
    """A distribution of an operating system, e.g. Debian GNU/Linux."""
    implements(IDistribution)

    _defaultOrder = 'name'

    name = StringCol(notNull=True, alternateID=True, unique=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    domainname = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    members = ForeignKey(dbName='members', foreignKey='Person', notNull=True)
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=False, default=None)
    translationpermission = EnumCol(dbName='translationpermission',
        notNull=True, schema=TranslationPermission,
        default=TranslationPermission.OPEN)
    lucilleconfig = StringCol(notNull=False, default=None)
    releases = MultipleJoin('DistroRelease', joinColumn='distribution',
                            orderBy=['version', 'datecreated', '-id'])
    bounties = RelatedJoin(
        'Bounty', joinColumn='distribution', otherColumn='bounty',
        intermediateTable='DistroBounty')
    bugtasks = MultipleJoin('BugTask', joinColumn='distribution')
    milestones = MultipleJoin('Milestone', joinColumn='distribution')
    specifications = MultipleJoin('Specification', joinColumn='distribution',
        orderBy=['-datecreated', 'id'])


    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistribution(self)
        return BugTaskSet().search(search_params)

    @property
    def open_cve_bugtasks(self):
        """See IDistribution."""
        result = BugTask.select("""
           CVERef.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distribution=%s AND
            BugTask.status IN (%s, %s)
            """ % sqlvalues(
                self.id,
                BugTaskStatus.NEW,
                BugTaskStatus.ACCEPTED),
            clauseTables=['Bug', 'CVERef'],
            orderBy=['-severity', 'datecreated'])
        return result

    @property
    def resolved_cve_bugtasks(self):
        """See IDistribution."""
        result = BugTask.select("""
            CVERef.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distribution=%s AND
            BugTask.status IN (%s, %s, %s)
            """ % sqlvalues(
                self.id,
                BugTaskStatus.REJECTED,
                BugTaskStatus.FIXED,
                BugTaskStatus.PENDINGUPLOAD),
            clauseTables=['Bug', 'CVERef'],
            orderBy=['-severity', 'datecreated'])
        return result

    @property
    def currentrelease(self):
        # if we have a frozen one, return that
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.FROZEN:
                return rel
        # if we have one in development, return that
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.DEVELOPMENT:
                return rel
        # if we have a stable one, return that
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.CURRENT:
                return rel
        # if we have ANY, return the first one
        if len(self.releases) > 0:
            return self.releases[0]
        return None

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
            query = query % (quote(self.id), severity)
            count = BugTask.select(query, clauseTables=clauseTables).count()
            counts.append(count)

        return counts
    bugCounter = property(bugCounter)

    def getRelease(self, name_or_version):
        """See IDistribution."""
        distrorelease = DistroRelease.selectOneBy(
            distributionID=self.id, name=name_or_version)
        if distrorelease is None:
            distrorelease = DistroRelease.selectOneBy(
                distributionID=self.id, version=name_or_version)
            if distrorelease is None:
                raise NotFoundError(name_or_version)
        return distrorelease

    def getDevelopmentReleases(self):
        """See IDistribution."""
        return DistroRelease.selectBy(
            distributionID = self.id,
            releasestatus = DistributionReleaseStatus.DEVELOPMENT)

    def getSourcePackage(self, name):
        """See IDistribution."""
        return SourcePackage(name, self.currentrelease)

    def getMilestone(self, name):
        """See IDistribution."""
        return Milestone.selectOne("""
            distribution = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return Specification.selectOneBy(distributionID=self.id, name=name)

    def ensureRelatedBounty(self, bounty):
        """See IDistribution."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        linker = DistributionBounty(distribution=self, bounty=bounty)
        return None


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
            raise NotFoundError(name)

    def get(self, distributionid):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        return Distribution.get(distributionid)

    def count(self):
        return Distribution.select().count()

    def getDistros(self):
        """Returns all Distributions available on the database"""
        return Distribution.select()

    def getByName(self, name):
        """Returns a Distribution with name = name"""
        return self[name]

    def new(self, name, displayname, title, description, summary, domainname,
            members, owner):
        return Distribution(
            name=name,
            displayname=displayname,
            title=title,
            description=description,
            summary=summary,
            domainname=domainname,
            members=members,
            owner=owner)

class DistroPackageFinder:

    implements(IDistroPackageFinder)

    def __init__(self, distribution=None, processorfamily=None):
        self.distribution = distribution
        # XXX kiko: and what about processorfamily?

