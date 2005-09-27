# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'SourcePackage',
    'SourcePackageSet',
    'DistroSourcePackage',
    'DistroSourcePackageSet']

import sets

from zope.interface import implements
from zope.component import getUtility

from sqlobject import SQLObjectNotFound

from canonical.database.sqlbase import (quote, sqlvalues,
    flush_database_updates)
from canonical.database.constants import UTC_NOW

from canonical.lp.dbschema import (
    BugTaskStatus, BugTaskSeverity, PackagePublishingStatus, PackagingType,
    PackagePublishingPocket)

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    ISourcePackage, IDistroSourcePackage, ISourcePackageSet,
    IDistroSourcePackageSet, ILaunchpadCelebrities)

from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.maintainership import Maintainership
from canonical.launchpad.database.vsourcepackagereleasepublishing import (
    VSourcePackageReleasePublishing)
from canonical.launchpad.database.sourcepackageindistro import (
    SourcePackageInDistro)
from canonical.launchpad.database.publishing import SourcePackagePublishing
from canonical.launchpad.database.publishedpackage import PublishedPackage
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.ticket import Ticket
from canonical.launchpad.validators.name import valid_name
from sourcerer.deb.version import Version


class SourcePackage:
    """A source package, e.g. apache2, in a distribution or distrorelease.
    This object implements the MagicSourcePackage specification. It is not a
    true database object, but rather attempts to represent the concept of a
    source package in a distribution, with links to the relevant database
    objects.

    Note that the Magic SourcePackage can be initialised with EITHER a
    distrorelease OR a distribution. This means you can specify either
    "package foo in ubuntu" or "package foo in warty", and then methods
    should work as expected.
    """

    implements(ISourcePackage)

    def __init__(self, sourcepackagename, distrorelease=None,
                 distribution=None):
        """SourcePackage requires a SourcePackageName and a
        DistroRelease or Distribution. These must be Launchpad
        database objects. If you give it a Distribution, it will try to find
        and use the Distribution.currentrelease, failing if that is not
        possible.
        """
        if distribution and distrorelease:
            raise TypeError(
                'Cannot initialise SourcePackage with both distro and'
                ' distrorelease.')
        self.sourcepackagename = sourcepackagename
        self.distrorelease = distrorelease
        if distribution:
            self.distrorelease = distribution.currentrelease
            if not self.distrorelease:
                raise ValueError(
                    "Distro '%s' has no current release" % distribution.name)
        # Set self.currentrelease based on current published sourcepackage
        # with this name in the distrorelease.  If none is published, leave
        # self.currentrelease as None

        # XXX: Daniel Debonzi
        # Getting only for pocket RELEASE.. to do not get more than one result.
        # Figure out what should be done to access another pockets
        package = SourcePackageInDistro.selectOneBy(
            sourcepackagenameID=sourcepackagename.id,
            distroreleaseID=self.distrorelease.id,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
        if package is None:
            self.currentrelease = None
        else:
            self.currentrelease = SourcePackageRelease.get(package.id)

    def _get_ubuntu(self):
        """This is a temporary measure while
        getUtility(IlaunchpadCelebrities) is bustificated here."""
        # XXX: fix and get rid of this and clean up callsites
        #   -- kiko, 2005-09-23
        from canonical.launchpad.database.distribution import Distribution
        return Distribution.byName('ubuntu')

    @property
    def displayname(self):
        return "%s %s" % (
            self.distrorelease.displayname, self.sourcepackagename.name)

    @property
    def title(self):
        titlestr = self.sourcepackagename.name
        titlestr += ' in ' + self.distribution.displayname
        titlestr += ' ' + self.distrorelease.displayname
        return titlestr

    @property
    def distribution(self):
        return self.distrorelease.distribution

    @property
    def distro(self):
        return self.distribution

    @property
    def format(self):
        if not self.currentrelease:
            return None
        return self.currentrelease.format

    @property
    def changelog(self):
        """See ISourcePackage"""

        clauseTables = ('SourcePackageName', 'SourcePackageRelease',
                        'SourcePackagePublishing','DistroRelease')

        query = ('SourcePackageRelease.sourcepackagename = '
                 'SourcePackageName.id AND '
                 'SourcePackageName = %d AND '
                 'SourcePackagePublishing.distrorelease = '
                 'DistroRelease.Id AND '
                 'SourcePackagePublishing.distrorelease = %d AND '
                 'SourcePackagePublishing.sourcepackagerelease = '
                 'SourcePackageRelease.id'
                 % (self.sourcepackagename.id,
                    self.distrorelease.id)
                 )

        spreleases = SourcePackageRelease.select(query,
                                                 clauseTables=clauseTables,
                                                 orderBy='version').reversed()
        changelog = ''

        for spr in spreleases:
            changelog += '%s \n\n' % spr.changelog

        return changelog

    @property
    def manifest(self):
        """For the moment, the manifest of a SourcePackage is defined as the
        manifest of the .currentrelease of that SourcePackage in the
        distrorelease. In future, we might have a separate table for the
        current working copy of the manifest for a source package.
        """
        if not self.currentrelease:
            return None
        return self.currentrelease.manifest

    @property
    def maintainer(self):
        querystr = "distribution=%s AND sourcepackagename=%s"
        querystr %= sqlvalues(self.distribution, self.sourcepackagename)
        return Maintainership.select(querystr)

    @property
    def releases(self):
        """See ISourcePackage."""
        ret = SourcePackageRelease.select('''
            SourcePackageRelease.sourcepackagename = %d AND
            SourcePackagePublishingHistory.distrorelease = %d AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id
            ''' % (self.sourcepackagename.id, self.distrorelease.id),
            clauseTables=['SourcePackagePublishingHistory'])

        # sort by debian version number
        return sorted(list(ret), key=lambda item: Version(item.version))

    @property
    def releasehistory(self):
        """See ISourcePackage."""
        ret = SourcePackageRelease.select('''
            SourcePackageRelease.sourcepackagename = %d AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %d
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id
            ''' % (self.sourcepackagename.id, self.distribution.id),
            clauseTables=['SourcePackagePublishingHistory'])

        # sort by debian version number
        return sorted(list(ret), key=lambda item: Version(item.version))

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def bugtasks(self):
        querystr = "distribution=%s AND sourcepackagename=%s" % sqlvalues(
            self.distribution.id, self.sourcepackagename.id)
        return BugTask.select(querystr)

    @property
    def potemplates(self):
        result = POTemplate.selectBy(
            distroreleaseID=self.distrorelease.id,
            sourcepackagenameID=self.sourcepackagename.id)
        return sorted(list(result), key=lambda x: x.potemplatename.name)

    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(
            distroreleaseID=self.distrorelease.id,
            sourcepackagenameID=self.sourcepackagename.id,
            iscurrent=True)
        return sorted(list(result), key=lambda x: x.potemplatename.name)

    @property
    def product(self):
        # we have moved to focusing on productseries as the linker
        from warnings import warn
        warn('SourcePackage.product is deprecated, use .productseries',
             DeprecationWarning, stacklevel=2)
        ps = self.productseries
        if ps is not None:
            return ps.product
        return None

    @property
    def productseries(self):
        # See if we can find a relevant packaging record
        packaging = self.packaging
        if packaging is None:
            return None
        return packaging.productseries

    @property
    def direct_packaging(self):
        """See ISourcePackage."""
        # get any packagings matching this sourcepackage
        packagings = Packaging.selectBy(
            sourcepackagenameID=self.sourcepackagename.id,
            distroreleaseID=self.distrorelease.id,
            orderBy='packaging')
        # now, return any Primary Packaging's found
        for pkging in packagings:
            if pkging.packaging == PackagingType.PRIME:
                return pkging
        # ok, we're scraping the bottom of the barrel, send the first
        # packaging we have
        if packagings.count() > 0:
            return packagings[0]
        # capitulate
        return None

    @property
    def packaging(self):
        """See ISourcePackage.packaging"""
        # First we look to see if there is packaging data for this
        # distrorelease and sourcepackagename. If not, we look up through
        # parent distroreleases, and when we hit Ubuntu, we look backwards in
        # time through Ubuntu releases till we find packaging information or
        # blow past the Warty Warthog.

        # see if there is a direct packaging
        result = self.direct_packaging
        if result is not None:
            return result

        # ubuntu is used as a special case below
        #ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        ubuntu = self._get_ubuntu()

        # if we are an ubuntu sourcepackage, try the previous release of
        # ubuntu
        if self.distribution == ubuntu:
            ubuntureleases = self.distrorelease.previous_releases
            if ubuntureleases.count() > 0:
                previous_ubuntu_release = ubuntureleases[0]
                sp = SourcePackage(sourcepackagename=self.sourcepackagename,
                                   distrorelease=previous_ubuntu_release)
                return sp.packaging
        # if we have a parent distrorelease, try that
        if self.distrorelease.parentrelease is not None:
            sp = SourcePackage(sourcepackagename=self.sourcepackagename,
                               distrorelease=self.distrorelease.parentrelease)
            return sp.packaging
        # capitulate
        return None


    @property
    def shouldimport(self):
        """Note that this initial implementation of the method knows that we
        are only interested in importing ubuntu packages initially. Also, it
        knows that we should only import packages where the upstream
        revision control is in place and working.
        """

        # ubuntu is used as a special case below
        #ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        ubuntu = self._get_ubuntu()

        if self.distribution != ubuntu:
            return False
        ps = self.productseries
        if ps is None:
            return False
        return ps.branch is not None

    @property
    def published_by_pocket(self):
        """See ISourcePackage."""
        result = SourcePackagePublishing.select("""
            SourcePackagePublishing.distrorelease = %s AND
            SourcePackagePublishing.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s
            """ % sqlvalues(
                self.distrorelease.id,
                self.sourcepackagename.id),
            clauseTables=['SourcePackageRelease'])
        # create the dictionary with the set of pockets as keys
        thedict = {}
        for pocket in PackagePublishingPocket.items:
            thedict[pocket] = []
        # add all the sourcepackagereleases in the right place
        for spr in result:
            thedict[spr.pocket].append(spr.sourcepackagerelease)
        return thedict

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setSourcePackage(self)
        return BugTaskSet().search(search_params)

    def setPackaging(self, productseries, user):
        target = self.direct_packaging
        if target is not None:
            # we should update the current packaging
            target.productseries = productseries
            target.owner = user
            target.datecreated = UTC_NOW
        else:
            # ok, we need to create a new one
            Packaging(distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename,
            productseries=productseries, owner=user,
            packaging=PackagingType.PRIME)
        # and make sure this change is immediately available
        flush_database_updates()

    def bugsCounter(self):
        # XXX: where does self.bugs come from?
        #   -- kiko, 2005-09-23
        ret = [len(self.bugs)]
        severities = [
            BugTaskSeverity.CRITICAL,
            BugTaskSeverity.MAJOR,
            BugTaskSeverity.NORMAL,
            BugTaskSeverity.MINOR,
            BugTaskSeverity.WISHLIST,
            BugTaskStatus.FIXED,
            BugTaskStatus.ACCEPTED,
            ]
        for severity in severities:
            n = BugTask.selectBy(
                severity=int(severity),
                sourcepackagenameID=self.sourcepackagename.id,
                distributionID=self.distribution.id).count()
            ret.append(n)
        return ret

    def getVersion(self, version):
        """This will look for a sourcepackage release with the given version
        in the distribution of this sourcepackage, NOT just the
        distrorelease of the sourcepackage. NB - this assumes that a given
        sourcepackagerelease version is UNIQUE in a distribution. This is
        true of Ubuntu, RedHat and similar distros, but might not be
        universally true. Please update when PublishingMorgue spec is
        implemented to use the full publishing history.
        """
        return VSourcePackageReleasePublishing.selectOneBy(
            sourcepackagename=self.sourcepackagename,
            distribution=self.distribution,
            version=version)

    @property
    def pendingrelease(self):
        # XXX: This needs a system doc test and a page test.
        #      It had an obvious error in it.
        #      SteveAlexander, 2005-04-25
        ret = VSourcePackageReleasePublishing.selectOneBy(
                sourcepackagenameID=self.sourcepackagename.id,
                publishingstatus=PackagePublishingStatus.PENDING,
                distroreleaseID = self.distrorelease.id)
        if ret is None:
            return None
        return SourcePackageRelease.get(ret.id)

    @property
    def publishedreleases(self):
        ret = VSourcePackageReleasePublishing.selectBy(
                sourcepackagenameID=self.sourcepackagename.id,
                publishingstatus=[PackagePublishingStatus.PUBLISHED,
                                  PackagePublishingStatus.SUPERSEDED],
                distroreleaseID = self.distrorelease.id)
        if ret.count() == 0:
            return None
        return shortlist(ret)

    # ticket related interfaces
    @property
    def tickets(self):
        """See ITicketTarget."""
        ret = Ticket.selectBy(distributionID=self.distribution.id,
            sourcepackagenameID=self.sourcepackagename.id)
        return ret.orderBy('-datecreated')

    def newTicket(self, owner, title, description):
        """See ITicketTarget."""
        return Ticket(title=title, description=description, owner=owner,
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


class DistroSourcePackage:
    """See canonical.launchpad.interfaces.IDistroSourcePackage."""

    implements(IDistroSourcePackage)

    def __init__(self, distribution, sourcepackagename):
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename
        package = SourcePackageInDistro.selectOneBy(
            sourcepackagenameID=sourcepackagename.id,
            distroreleaseID=distribution.currentrelease.id,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

        if package is None:
            self.currentrelease = None
        else:
            self.currentrelease = SourcePackageRelease.get(package.id)

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def displayname(self):
        return "%s %s" % (
            self.distribution.name, self.sourcepackagename.name)

    @property
    def title(self):
        return "%s %s" % (
            self.distribution.name, self.sourcepackagename.name)

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setSourcePackage(self)
        return BugTaskSet().search(search_params)


class SourcePackageSet(object):
    """A set of Magic SourcePackage objects."""

    implements(ISourcePackageSet)

    def __init__(self, distribution=None, distrorelease=None):
        if distribution is not None and distrorelease is not None:
            if distrorelease.distribution is not distribution:
                raise TypeError(
                    'Must instantiate SourcePackageSet with distribution'
                    ' or distrorelease, not both.')
        if distribution:
            self.distribution = distribution
            self.distrorelease = distribution.currentrelease
            self.title = distribution.title
        elif distrorelease:
            self.distribution = distrorelease.distribution
            self.distrorelease = distrorelease
            self.title = distrorelease.title
        else:
            self.title = ""
        self.title += " Source Packages"

    def __getitem__(self, name):
        try:
            spname = SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, 'No source package name %s' % name
        return SourcePackage(sourcepackagename=spname,
                             distrorelease=self.distrorelease)

    def __iter__(self, text=None):
        querystr = self._querystr(text)
        for row in VSourcePackageReleasePublishing.select(querystr):
            yield row

    def _querystr(self, text=None):
        querystr = ''
        if self.distrorelease:
            querystr += ('distrorelease = %s'
                         %  sqlvalues(self.distrorelease.id))
        if text:
            if len(querystr):
                querystr += ' AND '
            querystr += "name ILIKE " + quote('%%' + text + '%%')
        return querystr

    def query(self, text=None):
        querystr = self._querystr(text)
        for row in VSourcePackageReleasePublishing.select(querystr):
            yield SourcePackage(sourcepackagename=row.sourcepackagename,
                                distrorelease=row.distrorelease)

    def withBugs(self):
        pkgset = sets.Set()
        results = BugTask.select(
            "distribution = %s AND sourcepackagename IS NOT NULL" % sqlvalues(
            self.distribution.id))
        for task in results:
            pkgset.add(task.sourcepackagename)

        return [SourcePackage(sourcepackagename=sourcepackagename,
                              distribution=self.distribution)
                for sourcepackagename in pkgset]

    def getPackageNames(self, pkgname):
        """See ISourcePackageset.getPackagenames"""

        # we should only ever get a pkgname as a string
        assert isinstance(pkgname, str), "Only ever call this with a string"

        # clean it up and make sure it's a valid package name
        pkgname = pkgname.strip().lower()
        if not valid_name(pkgname):
            raise ValueError('Invalid package name: %s' % pkgname)

        # ubuntu is used as a special case below
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        #ubuntu = self._get_ubuntu()

        # first, we try assuming it's a binary package. let's try and find
        # a binarypackagename for it
        binarypackagename = BinaryPackageName.selectOneBy(name=pkgname)
        if binarypackagename is None:
            # maybe it's a sourcepackagename?
            sourcepackagename = SourcePackageName.selectOneBy(name=pkgname)
            if sourcepackagename is not None:
                # it's definitely only a sourcepackagename. let's make sure it
                # is published in the target ubuntu release
                publishing = SourcePackagePublishing.select('''
                    SourcePackagePublishing.distrorelease = %s AND
                    SourcePackagePublishing.sourcepackagerelease =
                        SourcePackageRelease.id AND
                    SourcePackageRelease.sourcepackagename = %s
                    ''' % sqlvalues(ubuntu.currentrelease.id,
                        sourcepackagename.id),
                    clauseTables=['SourcePackageRelease'],
                    distinct=True).count()
                if publishing == 0:
                    # yes, it's a sourcepackage, but we don't know about it in
                    # ubuntu
                    raise ValueError('Unpublished source package: %s' % pkgname)
                return (sourcepackagename, None)
            # it's neither a sourcepackage, nor a binary package name
            raise ValueError('Unknown package: %s' % pkgname)

        # ok, so we have a binarypackage with that name. let's see if it's
        # published, and what it's sourcepackagename is
        publishings = PublishedPackage.selectBy(
            binarypackagename=binarypackagename.name,
            distrorelease=ubuntu.currentrelease.id,
            orderBy=['id'])
        if publishings.count() == 0:
            # ok, we have a binary package name, but it's not published in the
            # target ubuntu release. let's see if it's published anywhere
            publishings = PublishedPackage.selectBy(
                binarypackagename=binarypackagename.name,
                orderBy=['id'])
            if publishings.count() == 0:
                # no publishing records anywhere for this beast, sadly
                raise ValueError('Unpublished binary package: %s' % pkgname)
        # PublishedPackageView uses the actual text names
        for p in publishings:
            sourcepackagenametxt = p.sourcepackagename
            break
        sourcepackagename = SourcePackageName.byName(sourcepackagenametxt)
        return (sourcepackagename, binarypackagename)


class DistroSourcePackageSet:
    """See canonical.launchpad.interfaces.IDistroSourcePackageSet."""

    implements(IDistroSourcePackageSet)

    def getPackage(self, distribution, sourcepackagename):
        """See canonical.launchpad.interfaces.IDistroSourcePackageSet."""
        return DistroSourcePackage(
            distribution=distribution, sourcepackagename=sourcepackagename)
