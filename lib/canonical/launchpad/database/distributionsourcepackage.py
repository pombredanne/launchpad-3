# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent source packages in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackage',
    ]

from sqlobject import SQLObjectNotFound

from zope.interface import implements

from canonical.launchpad.interfaces import IDistributionSourcePackage

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database.bug import BugSet
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.distributionsourcepackagecache import \
    DistributionSourcePackageCache
from canonical.launchpad.database.distributionsourcepackagerelease import \
    DistributionSourcePackageRelease
from canonical.launchpad.database.publishing import \
    SourcePackagePublishingHistory
from canonical.launchpad.database.sourcepackagerelease import \
    SourcePackageRelease
from canonical.launchpad.database.ticket import Ticket
from sourcerer.deb.version import Version
from canonical.launchpad.helpers import shortlist


class DistributionSourcePackage:
    """This is a "Magic Distribution Source Package". It is not an
    SQLObject, but instead it represents a source package with a particular
    name in a particular distribution. You can then ask it all sorts of
    things about the releases that are published under its name, the latest
    or current release, etc.
    """

    implements(IDistributionSourcePackage)

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
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.version = %s
            """ % sqlvalues(self.distribution.id, self.sourcepackagename.id,
                            version),
            orderBy='-datecreated',
            clauseTables=['distrorelease', 'sourcepackagerelease'])
        if spph.count() == 0:
            return None
        return DistributionSourcePackageRelease(
            distribution=self.distribution,
            sourcepackagerelease=spph[0].sourcepackagerelease)

    @property
    def currentrelease(self):
        """See IDistributionSourcePackage."""
        sprs = SourcePackageRelease.select("""
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.id =
                SourcePackagePublishing.sourcepackagerelease AND
            SourcePackagePublishing.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s
            """ % sqlvalues(self.sourcepackagename.id,
                            self.distribution.id),
            orderBy='datecreated',
            clauseTables=['SourcePackagePublishing', 'DistroRelease'])

        # sort by version
        releases = sorted(shortlist(sprs),
            key=lambda item: Version(item.version))
        if len(releases) == 0:
            return None
        return DistributionSourcePackageRelease(
            distribution=self.distribution,
            sourcepackagerelease=releases[-1])

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
    def binary_package_names(self):
        """See IDistributionSourcePackage."""
        cache = DistributionSourcePackageCache.selectOne("""
            distribution = %s AND
            sourcepackagename = %s
            """ % sqlvalues(self.distribution.id, self.sourcepackagename.id))
        if cache is None:
            return None
        return cache.binpkgnames

    @property
    def by_distroreleases(self):
        """See IDistributionSourcePackage."""
        # XXX, Brad Bollenbach, 2005-10-24: DistroReleaseSourcePackage is not
        # even imported into this module. This suggests that this method is an
        # unused/untested code path. See
        # See https://launchpad.net/products/launchpad/+bug/3531.
        result = []
        for release in self.releases:
            candidate = DistroReleaseSourcePackage(release,
                self.sourcepackagename)
            if candidate.was_uploaded:
                result.append(candidate)
        return result

    @property
    def publishing_history(self):
        """See IDistributionSourcePackage."""
        return SourcePackagePublishingHistory.select("""
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagename.id),
            clauseTables=['DistroRelease', 'SourcePackageRelease'],
            orderBy='-datecreated')

    @property
    def releases(self):
        """See IDistributionSourcePackage."""
        ret = SourcePackagePublishingHistory.select("""
            sourcepackagepublishinghistory.distrorelease = distrorelease.id AND
            distrorelease.distribution = %s AND
            sourcepackagepublishinghistory.sourcepackagerelease =
                sourcepackagerelease.id AND
            sourcepackagerelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution.id, self.sourcepackagename.id),
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

    # ticket related interfaces
    def tickets(self, quantity=None):
        """See ITicketTarget."""
        return Ticket.select("""
            distribution=%s AND
            sourcepackagename=%s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagename.id),
            orderBy='-datecreated',
            limit=quantity)

    def newTicket(self, owner, title, description):
        """See ITicketTarget."""
        return Ticket(
            title=title, description=description, owner=owner,
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)

    def getTicket(self, ticket_num):
        """See ITicketTarget."""
        # first see if there is a ticket with that number
        try:
            ticket = Ticket.get(ticket_num)
        except SQLObjectNotFound:
            return None
        # now verify that that ticket is actually for this target
        if ticket.distribution != self.distribution:
            return None
        if ticket.sourcepackagename != self.sourcepackagename:
            return None
        return ticket

    def __eq__(self, other):
        """See IDistributionSourcePackage."""
        return (
            (IDistributionSourcePackage.providedBy(other)) and
            (self.distribution.id == other.distribution.id) and
            (self.sourcepackagename.id == other.sourcepackagename.id))

    def __ne__(self, other):
        """See IDistributionSourcePackage."""
        return not self.__eq__(other)

    def searchTasks(self, search_params):
        """See IBugTarget."""
        search_params.setSourcePackage(self)
        return BugTaskSet().search(search_params)

    def createBug(self, owner, title, comment, private=False):
        """See IBugTarget."""
        return BugSet().createBug(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            owner=owner, title=title, comment=comment,
            private=private)
