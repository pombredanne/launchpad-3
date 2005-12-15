# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Distribution', 'DistributionSet', 'DistroPackageFinder']

from zope.interface import implements

from sqlobject import (
    RelatedJoin, SQLObjectNotFound, StringCol, ForeignKey, MultipleJoin)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.bug import BugSet
from canonical.launchpad.database.distributionbounty import DistributionBounty
from canonical.launchpad.database.distributionsourcepackage import (
    DistributionSourcePackage)
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.distributionsourcepackagecache import (
    DistributionSourcePackageCache)
from canonical.launchpad.database.distrorelease import DistroRelease
from canonical.launchpad.database.sourcepackagename import (
    SourcePackageName)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.specification import Specification
from canonical.launchpad.database.ticket import Ticket
from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing,
    SourcePackagePublishing)
from canonical.launchpad.database.publishedpackage import PublishedPackage
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.database.build import Build

from canonical.lp.dbschema import (
    EnumCol, BugTaskStatus, DistributionReleaseStatus,
    TranslationPermission, SpecificationSort)

from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IDistroPackageFinder, NotFoundError,
    IHasBuildRecords, ISourcePackageName, UNRESOLVED_BUGTASK_STATUSES,
    RESOLVED_BUGTASK_STATUSES)

from sourcerer.deb.version import Version

from canonical.launchpad.validators.name import valid_name


class Distribution(SQLBase):
    """A distribution of an operating system, e.g. Debian GNU/Linux."""
    implements(IDistribution, IHasBuildRecords)

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
    uploadsender = StringCol(notNull=False, default=None)
    uploadadmin = StringCol(notNull=False, default=None)

    bounties = RelatedJoin(
        'Bounty', joinColumn='distribution', otherColumn='bounty',
        intermediateTable='DistributionBounty')
    bugtasks = MultipleJoin('BugTask', joinColumn='distribution')
    milestones = MultipleJoin('Milestone', joinColumn='distribution')
    uploaders = MultipleJoin('DistroComponentUploader',
        joinColumn='distribution')
    source_package_caches = MultipleJoin('DistributionSourcePackageCache',
        joinColumn='distribution', orderBy='name')

    @property
    def releases(self):
        ret = DistroRelease.selectBy(distributionID=self.id)
        return sorted(ret, key=lambda a: Version(a.version), reverse=True)

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistribution(self)
        return BugTaskSet().search(search_params)

    def createBug(self, owner, title, comment, private=False):
        """See canonical.launchpad.interfaces.IBugTarget."""
        return BugSet().createBug(
            distribution=self, comment=comment, title=title, owner=owner,
            private=private)

    @property
    def open_cve_bugtasks(self):
        """See IDistribution."""
        open_bugtask_status_sql_values = "(%s)" % (
            ', '.join(sqlvalues(*UNRESOLVED_BUGTASK_STATUSES)))

        result = BugTask.select("""
            CVE.id = BugCve.cve AND
            BugCve.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distribution=%d AND
            BugTask.status IN %s
            """ % (self.id, open_bugtask_status_sql_values),
            clauseTables=['Bug', 'Cve', 'BugCve'],
            orderBy=['-severity', 'datecreated'])

        return result

    @property
    def resolved_cve_bugtasks(self):
        """See IDistribution."""
        resolved_bugtask_status_sql_values = "(%s)" % (
            ', '.join(sqlvalues(*RESOLVED_BUGTASK_STATUSES)))

        result = BugTask.select("""
            CVE.id = BugCve.cve AND
            BugCve.bug = Bug.id AND
            BugTask.bug = Bug.id AND
            BugTask.distribution=%d AND
            BugTask.status IN %s
            """ % (self.id, resolved_bugtask_status_sql_values),
            clauseTables=['Bug', 'Cve', 'BugCve'],
            orderBy=['-severity', 'datecreated'])
        return result

    @property
    def currentrelease(self):
        # If we have a frozen one, return that.
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.FROZEN:
                return rel
        # If we have one in development, return that.
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.DEVELOPMENT:
                return rel
        # If we have a stable one, return that.
        for rel in self.releases:
            if rel.releasestatus == DistributionReleaseStatus.CURRENT:
                return rel
        # If we have ANY, return the first one.
        if len(self.releases) > 0:
            return self.releases[0]
        return None

    def __getitem__(self, name):
        for release in self.releases:
            if release.name == name:
                return release
        raise NotFoundError(name)

    def __iter__(self):
        return iter(self.releases)

    def bugCounter(self):
        counts = []

        severities = [
            BugTaskStatus.NEW,
            BugTaskStatus.ACCEPTED,
            BugTaskStatus.REJECTED,
            BugTaskStatus.FIXED]

        query = ("bugtask.distribution = %s AND "
                 "bugtask.bugstatus = %i")

        for severity in severities:
            query = query % (quote(self.id), severity)
            count = BugTask.select(query).count()
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

    def getMilestone(self, name):
        """See IDistribution."""
        return Milestone.selectOne("""
            distribution = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def getSourcePackage(self, name):
        """See IDistribution."""
        if ISourcePackageName.providedBy(name):
            sourcepackagename = name
        else:
            try:
                sourcepackagename = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistributionSourcePackage(self, sourcepackagename)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See IDistribution."""
        return DistributionSourcePackageRelease(self, sourcepackagerelease)

    def specifications(self, sort=None, quantity=None):
        """See IHasSpecifications."""
        if sort is None or sort == SpecificationSort.DATE:
            order = ['-datecreated', 'id']
        elif sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'status', 'name']
        return Specification.selectBy(distributionID=self.id,
            orderBy=order)[:quantity]

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return Specification.selectOneBy(distributionID=self.id, name=name)

    def tickets(self, quantity=None):
        """See ITicketTarget."""
        return Ticket.select("""
            distribution = %s
            """ % sqlvalues(self.id),
            orderBy='-datecreated',
            limit=quantity)

    def newTicket(self, owner, title, description):
        """See ITicketTarget."""
        return Ticket(
            title=title, description=description, owner=owner,
            distribution=self)

    def getTicket(self, ticket_num):
        """See ITicketTarget."""
        # First see if there is a ticket with that number.
        try:
            ticket = Ticket.get(ticket_num)
        except SQLObjectNotFound:
            return None
        # Now verify that that ticket is actually for this target.
        if ticket.target != self:
            return None
        return ticket

    def ensureRelatedBounty(self, bounty):
        """See IDistribution."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        DistributionBounty(distribution=self, bounty=bounty)

    def getDistroReleaseAndPocket(self, distrorelease_name):
        """See IDistribution."""
        from canonical.archivepublisher.publishing import suffixpocket

        # Get the list of suffixes.
        suffixes = [suffix for suffix, ignored in suffixpocket.items()]
        # Sort it longest string first.
        suffixes.sort(key=len, reverse=True)

        for suffix in suffixes:
            if distrorelease_name.endswith(suffix):
                try:
                    left_size = len(distrorelease_name) - len(suffix)
                    return (self[distrorelease_name[:left_size]],
                            suffixpocket[suffix])
                except KeyError:
                    # Swallow KeyError to continue round the loop.
                    pass

        raise NotFoundError(distrorelease_name)

    def getFileByName(self, filename, source=True, binary=True):
        """See IDistribution."""
        assert (source or binary), "searching in an explicitly empty " \
               "space is pointless"
        if source:
            candidate = SourcePackageFilePublishing.selectOneBy(
                distribution=self.id,
                libraryfilealiasfilename=filename)
            if candidate is not None:
                return LibraryFileAlias.get(candidate.libraryfilealias)
        if binary:
            candidate = BinaryPackageFilePublishing.selectOneBy(
                distribution=self.id,
                libraryfilealiasfilename=filename)
            if candidate is not None:
                return LibraryFileAlias.get(candidate.libraryfilealias)
        raise NotFoundError(filename)


    def getBuildRecords(self, status=None, limit=10):
        """See IHasBuildRecords"""
        # Find out the distroarchreleases in question.
        ids_list = []
        for release in self.releases:
            ids = ','.join(
                '%d' % arch.id for arch in release.architectures)
            # Do not mess pgsql sintaxe with empty chunks.
            if ids:
                ids_list.append(ids)

        arch_ids = ','.join(ids_list)

        # If not distroarchrelease was found return None.
        if not arch_ids:
            return None

        # Specific status or simply touched by a builder.
        if status:
            status_clause = "buildstate=%s" % sqlvalues(status)
        else:
            status_clause = "builder is not NULL"

        return Build.select(
            "distroarchrelease IN (%s) AND %s" % (arch_ids, status_clause), 
            limit=limit, orderBy="-datebuilt")

    def removeOldCacheItems(self):
        """See IDistribution."""

        # Get the set of source package names to deal with.
        spns = set(SourcePackageName.select("""
            SourcePackagePublishing.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishing.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['SourcePackagePublishing', 'DistroRelease',
                'SourcePackageRelease']))

        # Remove the cache entries for packages we no longer publish.
        for cache in self.source_package_caches:
            if cache.sourcepackagename not in spns:
                cache.destroySelf()

    def updateCompleteSourcePackageCache(self, ztm=None):
        """See IDistribution."""

        # Get the set of source package names to deal with.
        spns = list(SourcePackageName.select("""
            SourcePackagePublishing.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishing.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['SourcePackagePublishing', 'DistroRelease',
                'SourcePackageRelease']))

        # Now update, committing every 50 packages.
        counter = 0
        for spn in spns:
            self.updateSourcePackageCache(spn)
            counter += 1
            if counter > 49:
                counter = 0
                if ztm is not None:
                    ztm.commit()

    def updateSourcePackageCache(self, sourcepackagename):
        """See IDistribution."""

        # Get the set of published sourcepackage releases.
        sprs = list(SourcePackageRelease.select("""
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.id =
                SourcePackagePublishing.sourcepackagerelease AND
            SourcePackagePublishing.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s
            """ % sqlvalues(sourcepackagename.id, self.id),
            orderBy='id',
            clauseTables=['SourcePackagePublishing', 'DistroRelease'],
            distinct=True))
        if len(sprs) == 0:
            return

        # Find or create the cache entry.
        cache = DistributionSourcePackageCache.selectOne("""
            distribution = %s AND
            sourcepackagename = %s
            """ % sqlvalues(self.id, sourcepackagename.id))
        if cache is None:
            cache = DistributionSourcePackageCache(
                distribution=self,
                sourcepackagename=sourcepackagename)

        # Make sure the name is correct.
        cache.name = sourcepackagename.name

        # Get the sets of binary package names, summaries, descriptions.
        binpkgnames = set()
        binpkgsummaries = set()
        binpkgdescriptions = set()
        for spr in sprs:
            binpkgs = BinaryPackageRelease.select("""
                BinaryPackageRelease.build = Build.id AND
                Build.sourcepackagerelease = %s
                """ % sqlvalues(spr.id),
                clauseTables=['Build'])
            for binpkg in binpkgs:
                binpkgnames.add(binpkg.name)
                binpkgsummaries.add(binpkg.summary)
                binpkgdescriptions.add(binpkg.description)

        # Update the caches.
        cache.binpkgnames = ' '.join(sorted(binpkgnames))
        cache.binpkgsummaries = ' '.join(sorted(binpkgsummaries))
        cache.binpkgdescriptions = ' '.join(sorted(binpkgdescriptions))

    def searchSourcePackages(self, text):
        """See IDistribution."""
        dspcaches = DistributionSourcePackageCache.select("""
            distribution = %s AND
            fti @@ ftq(%s)
            """ % sqlvalues(self.id, text),
            selectAlso='rank(fti, ftq(%s)) AS rank' % sqlvalues(text),
            orderBy=['-rank'],
            distinct=True)
        return [DistributionSourcePackage(
            distribution=self,
            sourcepackagename=dspc.sourcepackagename) for dspc in dspcaches]

    def getPackageNames(self, pkgname):
        """See IDistribution"""
        # XXX, Brad Bollenbach, 2005-10-24: This code is using undefined names,
        # SourcePackagePublishing and PublishedPackage. That almost surely means
        # this is an unused code path. See
        # https://launchpad.net/products/launchpad/+bug/3530.

        # We should only ever get a pkgname as a string.
        assert isinstance(pkgname, str), "Only ever call this with a string"

        # Clean it up and make sure it's a valid package name.
        pkgname = pkgname.strip().lower()
        if not valid_name(pkgname):
            raise ValueError('Invalid package name: %s' % pkgname)

        # First, we try assuming it's a binary package. let's try and find
        # a binarypackagename for it.
        binarypackagename = BinaryPackageName.selectOneBy(name=pkgname)
        if binarypackagename is None:
            # Is it a sourcepackagename?
            sourcepackagename = SourcePackageName.selectOneBy(name=pkgname)
            if sourcepackagename is not None:

                # XXX: completely untested code

                # It's definitely only a sourcepackagename. Let's make sure it
                # is published in the current distro release.
                publishing = SourcePackagePublishing.select('''
                    SourcePackagePublishing.distrorelease = %s AND
                    SourcePackagePublishing.sourcepackagerelease =
                        SourcePackageRelease.id AND
                    SourcePackageRelease.sourcepackagename = %s
                    ''' % sqlvalues(self.currentrelease.id,
                        sourcepackagename.id),
                    clauseTables=['SourcePackageRelease'],
                    distinct=True).count()
                if publishing == 0:
                    # Yes, it's a sourcepackage, but we don't know about it in
                    # this distro.
                    raise ValueError('Unpublished source package: %s' % pkgname)
                return (sourcepackagename, None)
            # It's neither a sourcepackage, nor a binary package name.
            raise ValueError('Unknown package: %s' % pkgname)

        # XXX: completely untested code

        # Ok, so we have a binarypackage with that name. let's see if it's
        # published, and what its sourcepackagename is.
        publishings = PublishedPackage.selectBy(
            binarypackagename=binarypackagename.name,
            distrorelease=self.currentrelease.id,
            orderBy=['id'])
        if publishings.count() == 0:
            # Ok, we have a binary package name, but it's not published in the
            # target distro release. let's see if it's published anywhere.
            publishings = PublishedPackage.selectBy(
                binarypackagename=binarypackagename.name,
                orderBy=['id'])
            if publishings.count() == 0:
                # There are no publishing records anywhere for this beast,
                # sadly.
                raise ValueError('Unpublished binary package: %s' % pkgname)

        # PublishedPackageView uses the actual text names.
        for p in publishings:
            sourcepackagenametxt = p.sourcepackagename
            break
        sourcepackagename = SourcePackageName.byName(sourcepackagenametxt)
        return (sourcepackagename, binarypackagename)


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
