# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Classes to represent source packages in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackage',
    ]

from sqlobject.sqlbuilder import SQLConstant

from zope.interface import implements

from canonical.launchpad.interfaces import (
    IDistributionSourcePackage, IQuestionTarget, DuplicateBugContactError,
    DeleteBugContactError, PackagePublishingStatus)
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database.bug import BugSet, get_bug_tags_open_count
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.distributionsourcepackagecache import (
    DistributionSourcePackageCache)
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.packagebugcontact import PackageBugContact
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.sourcepackage import (
    SourcePackage, SourcePackageQuestionTargetMixin)


class DistributionSourcePackage(BugTargetBase,
                                SourcePackageQuestionTargetMixin):
    """This is a "Magic Distribution Source Package". It is not an
    SQLObject, but instead it represents a source package with a particular
    name in a particular distribution. You can then ask it all sorts of
    things about the releases that are published under its name, the latest
    or current release, etc.
    """

    implements(IDistributionSourcePackage, IQuestionTarget)

    def __init__(self, distribution, sourcepackagename):
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename

    @property
    def name(self):
        """See IDistributionSourcePackage."""
        return self.sourcepackagename.name

    @property
    def displayname(self):
        """See IDistributionSourcePackage."""
        return '%s in %s' % (
            self.sourcepackagename.name, self.distribution.name)

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return "%s (%s)" % (self.name, self.distribution.displayname)

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return "%s (%s)" % (self.name, self.distribution.displayname)

    @property
    def title(self):
        """See IDistributionSourcePackage."""
        return 'Source Package "%s" in %s' % (
            self.sourcepackagename.name, self.distribution.title)

    def __getitem__(self, version):
        return self.getVersion(version)

    def getVersion(self, version):
        """See IDistributionSourcePackage."""
        spph = SourcePackagePublishingHistory.select("""
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.version = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagename,
                            version),
            orderBy='-datecreated',
            prejoinClauseTables=['SourcePackageRelease'],
            clauseTables=['DistroRelease', 'SourcePackageRelease'])
        if spph.count() == 0:
            return None
        return DistributionSourcePackageRelease(
            distribution=self.distribution,
            sourcepackagerelease=spph[0].sourcepackagerelease)

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def currentrelease(self):
        """See IDistributionSourcePackage."""
        order_const = "debversion_sort_key(SourcePackageRelease.version) DESC"
        spr = SourcePackageRelease.selectFirst("""
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.id =
                SourcePackagePublishingHistory.sourcepackagerelease AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.status != %s
            """ % sqlvalues(self.sourcepackagename,
                            self.distribution,
                            self.distribution.all_distro_archive_ids,
                            PackagePublishingStatus.REMOVED),
            clauseTables=['SourcePackagePublishingHistory', 'DistroRelease'],
            orderBy=[SQLConstant(order_const),
                     "-SourcePackagePublishingHistory.datepublished"])

        if spr is None:
            return None
        else:
            return DistributionSourcePackageRelease(
                distribution=self.distribution,
                sourcepackagerelease=spr)

    def bugtasks(self, quantity=None):
        """See IDistributionSourcePackage."""
        return BugTask.select("""
            distribution=%s AND
            sourcepackagename=%s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagename.id),
            orderBy='-datecreated',
            limit=quantity)

    @property
    def bugcontacts(self):
        """See IDistributionSourcePackage."""
        # Use "list" here because it's possible that this list will be longer
        # than a "shortlist", though probably uncommon.
        query = """
            PackageBugContact.distribution=%s
            AND PackageBugContact.sourcepackagename = %s
            AND PackageBugContact.bugcontact = Person.id
            """ % sqlvalues(self.distribution, self.sourcepackagename)
        contacts = PackageBugContact.select(
            query,
            orderBy='Person.displayname',
            clauseTables=['Person'])
        contacts.prejoin(["bugcontact"])
        return list(contacts)

    def addBugContact(self, person):
        """See IDistributionSourcePackage."""
        contact_already_exists = self.isBugContact(person)

        if contact_already_exists:
            raise DuplicateBugContactError(
                "%s is already one of the bug contacts for %s." %
                (person.name, self.displayname))
        else:
            PackageBugContact(
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename,
                bugcontact=person)

    def removeBugContact(self, person):
        """See IDistributionSourcePackage."""
        contact_to_remove = self.isBugContact(person)

        if not contact_to_remove:
            raise DeleteBugContactError("%s is not a bug contact for this package.")
        else:
            contact_to_remove.destroySelf()

    def isBugContact(self, person):
        """See IDistributionSourcePackage."""
        package_bug_contact = PackageBugContact.selectOneBy(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            bugcontact=person)

        if package_bug_contact:
            return package_bug_contact
        else:
            return False

    @property
    def binary_package_names(self):
        """See IDistributionSourcePackage."""
        cache = DistributionSourcePackageCache.selectOne("""
            distribution = %s AND
            sourcepackagename = %s
            """ % sqlvalues(self.distribution.id, self.sourcepackagename.id))
        if cache is None:
            return None
        return cache.binpkgnames

    def get_distroseries_packages(self, active_only=True):
        """See IDistributionSourcePackage."""
        result = []
        for series in self.distribution.serieses:
            if active_only:
                if not series.active:
                    continue
            candidate = SourcePackage(self.sourcepackagename, series)
            if candidate.currentrelease is not None:
                result.append(candidate)
        return result

    @property
    def publishing_history(self):
        """See IDistributionSourcePackage."""
        return self._getPublishingHistoryQuery()

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def current_publishing_records(self):
        """See IDistributionSourcePackage."""
        status = PackagePublishingStatus.PUBLISHED
        return self._getPublishingHistoryQuery(status)

    def _getPublishingHistoryQuery(self, status=None):
        query = """
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagename)

        if status is not None:
            query += ("AND SourcePackagePublishingHistory.status = %s"
                      % sqlvalues(status))

        return SourcePackagePublishingHistory.select(query,
            clauseTables=['DistroRelease', 'SourcePackageRelease'],
            prejoinClauseTables=['SourcePackageRelease'],
            orderBy='-datecreated')

    # XXX kiko 2006-08-16: Bad method name, no need to be a property.
    @property
    def releases(self):
        """See IDistributionSourcePackage."""
        ret = SourcePackagePublishingHistory.select("""
            sourcepackagepublishinghistory.distrorelease = DistroRelease.id AND
            DistroRelease.distribution = %s AND
            sourcepackagepublishinghistory.archive IN %s AND
            sourcepackagepublishinghistory.sourcepackagerelease =
                sourcepackagerelease.id AND
            sourcepackagerelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagename),
            orderBy='-datecreated',
            clauseTables=['distrorelease', 'sourcepackagerelease'])
        result = []
        versions = set()
        for spp in ret:
            if spp.sourcepackagerelease.version not in versions:
                versions.add(spp.sourcepackagerelease.version)
                dspr = DistributionSourcePackageRelease(
                    distribution=self.distribution,
                    sourcepackagerelease=spp.sourcepackagerelease)
                result.append(dspr)
        return result

    def __eq__(self, other):
        """See IDistributionSourcePackage."""
        return (
            (IDistributionSourcePackage.providedBy(other)) and
            (self.distribution.id == other.distribution.id) and
            (self.sourcepackagename.id == other.sourcepackagename.id))

    def __ne__(self, other):
        """See IDistributionSourcePackage."""
        return not self.__eq__(other)

    def _getBugTaskContextWhereClause(self):
        """See BugTargetBase."""
        return (
            "BugTask.distribution = %d AND BugTask.sourcepackagename = %d" % (
            self.distribution.id, self.sourcepackagename.id))

    def searchTasks(self, search_params):
        """See IBugTarget."""
        search_params.setSourcePackage(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return self.distribution.getUsedBugTags()

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.distribution = %s" % sqlvalues(self.distribution),
            user,
            count_subcontext_clause="BugTask.sourcepackagename = %s" % (
                sqlvalues(self.sourcepackagename)))

    def createBug(self, bug_params):
        """See IBugTarget."""
        bug_params.setBugTarget(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)
        return BugSet().createBug(bug_params)

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return (
            'BugTask.distribution = %s AND BugTask.sourcepackagename = %s' %
                sqlvalues(self.distribution, self.sourcepackagename))
