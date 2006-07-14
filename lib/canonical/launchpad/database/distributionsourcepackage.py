# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Classes to represent source packages in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackage',
    ]

import apt_pkg
apt_pkg.InitSystem()

from sqlobject import SQLObjectNotFound

from zope.interface import implements

from canonical.lp.dbschema import PackagePublishingStatus, TicketStatus

from canonical.launchpad.interfaces import (
    IDistributionSourcePackage, ITicketTarget, DuplicateBugContactError,
    DeleteBugContactError)
from canonical.launchpad.components.bugtarget import BugTargetBase
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.database.bug import BugSet
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
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.supportcontact import SupportContact
from canonical.launchpad.database.ticket import Ticket, TicketSet
from canonical.launchpad.helpers import shortlist

_arg_not_provided = object()

class DistributionSourcePackage(BugTargetBase):
    """This is a "Magic Distribution Source Package". It is not an
    SQLObject, but instead it represents a source package with a particular
    name in a particular distribution. You can then ask it all sorts of
    things about the releases that are published under its name, the latest
    or current release, etc.
    """

    implements(IDistributionSourcePackage, ITicketTarget)

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
            prejoinClauseTables=['SourcePackageRelease'],
            clauseTables=['DistroRelease', 'SourcePackageRelease'])
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

        # safely sort by version
        compare = lambda a,b: apt_pkg.VersionCompare(a.version, b.version)
        releases = sorted(shortlist(sprs), cmp=compare)
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
    def bugcontacts(self):
        """See IDistributionSourcePackage."""
        # Use "list" here because it's possible that this list will be longer
        # than a "shortlist", though probably uncommon.
        return list(PackageBugContact.selectBy(
            distributionID=self.distribution.id,
            sourcepackagenameID=self.sourcepackagename.id))

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
            distributionID=self.distribution.id,
            sourcepackagenameID=self.sourcepackagename.id,
            bugcontactID=person.id)

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

    @property
    def by_distroreleases(self):
        """See IDistributionSourcePackage."""
        result = []
        for release in self.distribution.releases:
            candidate = SourcePackage(self.sourcepackagename, release)
            if candidate.currentrelease:
                result.append(candidate)
        return result

    @property
    def publishing_history(self):
        """See IDistributionSourcePackage."""
        return self._getPublishingHistoryQuery()

    @property
    def current_publishing_records(self):
        """See IDistributionSourcePackage."""
        status = PackagePublishingStatus.PUBLISHED
        return self._getPublishingHistoryQuery(status)

    def _getPublishingHistoryQuery(self, status=None):
        query = """
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s
            """ % sqlvalues(self.distribution.id,
                            self.sourcepackagename.id)

        if status is not None:
            query += ("AND SourcePackagePublishingHistory.status = %s"
                      % sqlvalues(status))

        return SourcePackagePublishingHistory.select(query,
            clauseTables=['DistroRelease', 'SourcePackageRelease'],
            prejoinClauseTables=['SourcePackageRelease'],
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

    def newTicket(self, owner, title, description, datecreated=None):
        """See ITicketTarget."""
        return TicketSet.new(
            title=title, description=description, owner=owner,
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            datecreated=datecreated)

    def getTicket(self, ticket_id):
        """See ITicketTarget."""
        # first see if there is a ticket with that number
        try:
            ticket = Ticket.get(ticket_id)
        except SQLObjectNotFound:
            return None
        # now verify that that ticket is actually for this target
        if ticket.distribution != self.distribution:
            return None
        if ticket.sourcepackagename != self.sourcepackagename:
            return None
        return ticket

    def searchTickets(self, search_text=None,
                      status=(TicketStatus.OPEN, TicketStatus.ANSWERED),
                      sort=None):
        """See ITicketTarget."""
        return TicketSet.search(search_text=search_text, status=status,
                                sort=sort, distribution=self.distribution,
                                sourcepackagename=self.sourcepackagename)

    def addSupportContact(self, person):
        """See ITicketTarget."""
        if person in self.support_contacts:
            return False
        SupportContact(
            product=None, person=person.id,
            sourcepackagename=self.sourcepackagename.id,
            distribution=self.distribution.id)
        return True

    def removeSupportContact(self, person):
        """See ITicketTarget."""
        if person not in self.support_contacts:
            return False
        support_contact_entry = SupportContact.selectOneBy(
            distributionID=self.distribution.id,
            sourcepackagenameID=self.sourcepackagename.id,
            personID=person.id)
        support_contact_entry.destroySelf()
        return True

    @property
    def support_contacts(self):
        """See ITicketTarget."""
        support_contacts = SupportContact.selectBy(
            distributionID=self.distribution.id,
            sourcepackagenameID=self.sourcepackagename.id)

        return shortlist([
            support_contact.person for support_contact in support_contacts
            ],
            longest_expected=100)

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

    def createBug(self, owner, title, comment, security_related=False,
                  private=False, binarypackagename=None):
        """See IBugTarget."""
        return BugSet().createBug(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            binarypackagename=binarypackagename,
            owner=owner, title=title, comment=comment,
            security_related=security_related, private=private)
