# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

__all__ = [
    'DistroRelease',
    'DistroReleaseSet',
    ]

import logging
import psycopg
import random
import re
import time
from cStringIO import StringIO

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, SQLMultipleJoin, IntCol, SQLObjectNotFound,
    SQLRelatedJoin)

from canonical.cachedproperty import cachedproperty

from canonical.database import postgresql
from canonical.database.sqlbase import (quote_like, quote, quoteIdentifier,
    SQLBase, sqlvalues, flush_database_updates, cursor, flush_database_caches)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import (
    PackagePublishingStatus, DistributionReleaseStatus,
    DistroReleaseQueueStatus, PackagePublishingPocket, SpecificationSort,
    SpecificationGoalStatus, SpecificationFilter)

from canonical.launchpad.interfaces import (
    IDistroRelease, IDistroReleaseSet, ISourcePackageName,
    IPublishedPackageSet, IHasBuildRecords, NotFoundError,
    IBinaryPackageName, ILibraryFileAliasSet, IBuildSet,
    ISourcePackage, ISourcePackageNameSet,
    IHasQueueItems, IPublishing)

from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.bug import (
    get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.distroreleasebinarypackage import (
    DistroReleaseBinaryPackage)
from canonical.launchpad.database.distroreleasesourcepackagerelease import (
    DistroReleaseSourcePackageRelease)
from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache)
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory, SourcePackagePublishingHistory)
from canonical.launchpad.database.distroarchrelease import DistroArchRelease
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.distroreleaselanguage import (
    DistroReleaseLanguage, DummyDistroReleaseLanguage)
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.binarypackagerelease import (
        BinaryPackageRelease)
from canonical.launchpad.database.component import Component
from canonical.launchpad.database.section import Section
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.queue import (
    DistroReleaseQueue, PackageUploadQueue)
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.helpers import shortlist


class DistroRelease(SQLBase, BugTargetBase, HasSpecificationsMixin):
    """A particular release of a distribution."""
    implements(IDistroRelease, IHasBuildRecords, IHasQueueItems, IPublishing)

    _table = 'DistroRelease'
    _defaultOrder = ['distribution', 'version']

    distribution = ForeignKey(dbName='distribution',
                              foreignKey='Distribution', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    releasestatus = EnumCol(notNull=True, schema=DistributionReleaseStatus)
    date_created = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    datereleased = UtcDateTimeCol(notNull=False, default=None)
    parentrelease =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroRelease', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    driver = ForeignKey(
        foreignKey="Person", dbName="driver", notNull=False, default=None)
    lucilleconfig = StringCol(notNull=False, default=None)
    changeslist = StringCol(notNull=False, default=None)
    nominatedarchindep = ForeignKey(
        dbName='nominatedarchindep',foreignKey='DistroArchRelease',
        notNull=False, default=None)
    datelastlangpack = UtcDateTimeCol(dbName='datelastlangpack', notNull=False,
        default=None)
    messagecount = IntCol(notNull=True, default=0)
    binarycount = IntCol(notNull=True, default=DEFAULT)
    sourcecount = IntCol(notNull=True, default=DEFAULT)

    architectures = SQLMultipleJoin(
        'DistroArchRelease', joinColumn='distrorelease',
        orderBy='architecturetag')
    binary_package_caches = SQLMultipleJoin('DistroReleasePackageCache',
        joinColumn='distrorelease', orderBy='name')
    components = SQLRelatedJoin(
        'Component', joinColumn='distrorelease', otherColumn='component',
        intermediateTable='ComponentSelection')
    sections = SQLRelatedJoin(
        'Section', joinColumn='distrorelease', otherColumn='section',
        intermediateTable='SectionSelection')

    @property
    def all_milestones(self):
        """See IDistroRelease."""
        return Milestone.selectBy(
            distrorelease=self, orderBy=['dateexpected', 'name'])

    @property
    def milestones(self):
        """See IDistroRelease."""
        return Milestone.selectBy(
            distrorelease=self, visible=True, orderBy=['dateexpected', 'name'])

    @property
    def drivers(self):
        """See IDistroRelease."""
        drivers = set()
        drivers.add(self.driver)
        drivers = drivers.union(self.distribution.drivers)
        drivers.discard(None)
        return sorted(drivers, key=lambda driver: driver.browsername)

    @property
    def sortkey(self):
        """A string to be used for sorting distro releases.

        This is designed to sort alphabetically by distro and release name,
        except that Ubuntu will be at the top of the listing.
        """
        result = ''
        if self.distribution.name == 'ubuntu':
            result += '-'
        result += self.distribution.name + self.name
        return result

    @property
    def packagings(self):
        # We join through sourcepackagename to be able to ORDER BY it,
        # and this code also uses prejoins to avoid fetching data later
        # on.
        packagings = Packaging.select(
            "Packaging.sourcepackagename = SourcePackageName.id "
            "AND DistroRelease.id = Packaging.distrorelease "
            "AND DistroRelease.id = %d" % self.id,
            prejoinClauseTables=["SourcePackageName", "DistroRelease"],
            clauseTables=["SourcePackageName", "DistroRelease"],
            prejoins=["productseries", "productseries.product"],
            orderBy=["SourcePackageName.name"]
            )
        return packagings

    @property
    def distroreleaselanguages(self):
        result = DistroReleaseLanguage.select(
            "DistroReleaseLanguage.language = Language.id AND"
            " DistroReleaseLanguage.distrorelease = %d AND"
            " Language.visible = TRUE" % self.id,
            prejoinClauseTables=["Language"],
            clauseTables=["Language"],
            prejoins=["distrorelease"],
            orderBy=["Language.englishname"])
        return result

    @cachedproperty('_previous_releases_cached')
    def previous_releases(self):
        """See IDistroRelease."""
        # This property is cached because it is used intensely inside
        # sourcepackage.py; avoiding regeneration reduces a lot of
        # count(*) queries.
        datereleased = self.datereleased
        # if this one is unreleased, use the last released one
        if not datereleased:
            datereleased = 'NOW'
        results = DistroRelease.select('''
                distribution = %s AND
                datereleased < %s
                ''' % sqlvalues(self.distribution.id, datereleased),
                orderBy=['-datereleased'])
        return list(results)

    @property
    def parent(self):
        """See IDistroRelease."""
        if self.parentrelease:
            return self.parentrelease.title
        return ''

    def canUploadToPocket(self, pocket):
        """See IDistroRelease."""
        # frozen/released states
        released_states = [
            DistributionReleaseStatus.SUPPORTED,
            DistributionReleaseStatus.CURRENT
            ]

        # deny uploads for released RELEASE pockets
        if (pocket == PackagePublishingPocket.RELEASE and
            self.releasestatus in released_states):
            return False

        # deny uploads for non-RELEASE unreleased pockets
        if (pocket != PackagePublishingPocket.RELEASE and
            self.releasestatus not in released_states):
            return False

        # allow anything else
        return True

    def updatePackageCount(self):
        """See IDistroRelease."""

        # first update the source package count
        query = """
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.status = %s AND
            SourcePackagePublishingHistory.pocket = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self.id,
                            PackagePublishingStatus.PUBLISHED,
                            PackagePublishingPocket.RELEASE)
        self.sourcecount = SourcePackageName.select(
            query, distinct=True,
            clauseTables=['SourcePackageRelease',
                          'SourcePackagePublishingHistory']).count()


        # next update the binary count
        clauseTables = ['DistroArchRelease', 'BinaryPackagePublishingHistory',
                        'BinaryPackageRelease']
        query = """
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s AND
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingPocket.RELEASE,
                self.id)
        ret = BinaryPackageName.select(
            query, distinct=True, clauseTables=clauseTables).count()
        self.binarycount = ret

    @property
    def architecturecount(self):
        """See IDistroRelease."""
        return self.architectures.count()

    # XXX: this is expensive and shouldn't be a property
    #   -- kiko, 2006-06-14
    @property
    def potemplates(self):
        result = POTemplate.selectBy(distrorelease=self)
        result = result.prejoin(['potemplatename'])
        return sorted(result,
            key=lambda x: (-x.priority, x.potemplatename.name))

    # XXX: this is expensive and shouldn't be a property
    #   -- kiko, 2006-06-14
    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(distrorelease=self, iscurrent=True)
        result = result.prejoin(['potemplatename'])
        return sorted(result,
            key=lambda x: (-x.priority, x.potemplatename.name))

    @property
    def fullreleasename(self):
        return "%s %s" % (
            self.distribution.name.capitalize(), self.name.capitalize())

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return self.fullreleasename

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistributionRelease(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return get_bug_tags("BugTask.distrorelease = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.distrorelease = %s" % sqlvalues(self), user)

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None):
        """See IHasSpecifications.

        In this case the rules for the default behaviour cover three things:

          - acceptance: if nothing is said, ACCEPTED only
          - completeness: if nothing is said, ANY
          - informationalness: if nothing is said, ANY

        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a distrorelease is to show everything approved
            filter = [SpecificationFilter.ACCEPTED]

        # defaults for completeness: in this case we don't actually need to
        # do anything, because the default is ANY

        # defaults for acceptance: in this case, if nothing is said about
        # acceptance, we want to show only accepted specs
        acceptance = False
        for option in [
            SpecificationFilter.ACCEPTED,
            SpecificationFilter.DECLINED,
            SpecificationFilter.PROPOSED]:
            if option in filter:
                acceptance = True
        if acceptance is False:
            filter.append(SpecificationFilter.ACCEPTED)

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.status', 'Specification.name']
        elif sort == SpecificationSort.DATE:
            # we are showing specs for a GOAL, so under some circumstances
            # we care about the order in which the specs were nominated for
            # the goal, and in others we care about the order in which the
            # decision was made.

            # we need to establish if the listing will show specs that have
            # been decided only, or will include proposed specs.
            show_proposed = set([
                SpecificationFilter.ALL,
                SpecificationFilter.PROPOSED,
                ])
            if len(show_proposed.intersection(set(filter))) > 0:
                # we are showing proposed specs so use the date proposed
                # because not all specs will have a date decided.
                order = ['-Specification.datecreated', 'Specification.id']
            else:
                # this will show only decided specs so use the date the spec
                # was accepted or declined for the sprint
                order = ['-Specification.date_goal_decided',
                         '-Specification.datecreated',
                         'Specification.id']

        # figure out what set of specifications we are interested in. for
        # distroreleases, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - goal status.
        #  - informational.
        #
        base = 'Specification.distrorelease = %s' % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += ' AND Specification.informational IS TRUE'

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # look for specs that have a particular goalstatus (proposed,
        # accepted or declined)
        if SpecificationFilter.ACCEPTED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.ACCEPTED.value)
        elif SpecificationFilter.PROPOSED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.PROPOSED.value)
        elif SpecificationFilter.DECLINED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.DECLINED.value)

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        # now do the query, and remember to prejoin to people
        results = Specification.select(query, orderBy=order, limit=quantity)
        return results.prejoin(['assignee', 'approver', 'drafter'])

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.distribution.getSpecification(name)

    def getDistroReleaseLanguage(self, language):
        """See IDistroRelease."""
        return DistroReleaseLanguage.selectOneBy(
            distrorelease=self, language=language)

    def getDistroReleaseLanguageOrDummy(self, language):
        """See IDistroRelease."""
        drl = self.getDistroReleaseLanguage(language)
        if drl is not None:
            return drl
        return DummyDistroReleaseLanguage(self, language)

    def updateStatistics(self, ztm):
        """See IDistroRelease."""
        # first find the set of all languages for which we have pofiles in
        # the distribution
        langidset = set(
            language.id for language in Language.select('''
                Language.visible = TRUE AND
                Language.id = POFile.language AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distrorelease = %s AND
                POTemplate.iscurrent = TRUE
                ''' % sqlvalues(self.id),
                orderBy=['code'],
                distinct=True,
                clauseTables=['POFile', 'POTemplate'])
            )
        # now run through the existing DistroReleaseLanguages for the
        # distrorelease, and update their stats, and remove them from the
        # list of languages we need to have stats for
        for distroreleaselanguage in self.distroreleaselanguages:
            distroreleaselanguage.updateStatistics(ztm)
            langidset.discard(distroreleaselanguage.language.id)
        # now we should have a set of languages for which we NEED
        # to have a DistroReleaseLanguage
        for langid in langidset:
            drl = DistroReleaseLanguage(distrorelease=self, languageID=langid)
            drl.updateStatistics(ztm)
        # lastly, we need to update the message count for this distro
        # release itself
        messagecount = 0
        for potemplate in self.currentpotemplates:
            messagecount += potemplate.messageCount()
        self.messagecount = messagecount
        ztm.commit()

    def getSourcePackage(self, name):
        """See IDistroRelease."""
        if not ISourcePackageName.providedBy(name):
            try:
                name = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return SourcePackage(sourcepackagename=name, distrorelease=self)

    def getBinaryPackage(self, name):
        """See IDistroRelease."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroReleaseBinaryPackage(self, name)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See IDistroRelease."""
        return DistroReleaseSourcePackageRelease(self, sourcepackagerelease)

    def __getitem__(self, archtag):
        """See IDistroRelease."""
        item = DistroArchRelease.selectOneBy(
            distrorelease=self, architecturetag=archtag)
        if item is None:
            raise NotFoundError('Unknown architecture %s for %s %s' % (
                archtag, self.distribution.name, self.name))
        return item

    def getTranslatableSourcePackages(self):
        """See IDistroRelease."""
        query = """
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.iscurrent = TRUE AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id)
        result = SourcePackageName.select(query, clauseTables=['POTemplate'],
            orderBy=['name'], distinct=True)
        return [SourcePackage(sourcepackagename=spn, distrorelease=self) for
            spn in result]

    def getUnlinkedTranslatableSourcePackages(self):
        """See IDistroRelease."""
        # Note that both unlinked packages and
        # linked-with-no-productseries packages are considered to be
        # "unlinked translatables".
        query = """
            SourcePackageName.id NOT IN (SELECT DISTINCT
             sourcepackagename FROM Packaging WHERE distrorelease = %s) AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id, self.id)
        unlinked = SourcePackageName.select(query, clauseTables=['POTemplate'],
              orderBy=['name'])
        query = """
            Packaging.sourcepackagename = SourcePackageName.id AND
            Packaging.productseries = NULL AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id)
        linked_but_no_productseries = SourcePackageName.select(query,
            clauseTables=['POTemplate', 'Packaging'], orderBy=['name'])
        result = unlinked.union(linked_but_no_productseries)
        return [SourcePackage(sourcepackagename=spn, distrorelease=self) for
            spn in result]

    def getPublishedReleases(self, sourcepackage_or_name, version=None,
            pocket=None, include_pending=False, exclude_pocket=None):
        """See IDistroRelease."""
        # XXX cprov 20060213: we need a standard and easy API, no need
        # to support multiple type arguments, only string name should be
        # the best choice in here, the call site will be clearer.
        # bug # 31317
        if ISourcePackage.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name.name
        elif ISourcePackageName.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name
        else:
            spns = getUtility(ISourcePackageNameSet)
            spn = spns.queryByName(sourcepackage_or_name)
            if spn is None:
                return []

        queries = ["""
        sourcepackagerelease=sourcepackagerelease.id AND
        sourcepackagerelease.sourcepackagename=%s AND
        distrorelease=%s
        """ % sqlvalues(spn.id, self.id)]

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if version is not None:
            queries.append("version=%s" % sqlvalues(version))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        published = SourcePackagePublishingHistory.select(
            " AND ".join(queries),
            clauseTables = ['SourcePackageRelease'])

        return shortlist(published)

    def isUnstable(self):
        """See IDistroRelease."""
        return self.releasestatus in [
            DistributionReleaseStatus.FROZEN,
            DistributionReleaseStatus.DEVELOPMENT,
            DistributionReleaseStatus.EXPERIMENTAL,
        ]

    def getAllReleasesByStatus(self, status):
        """See IDistroRelease."""
        queries = ['distrorelease=%s AND status=%s'
                   % sqlvalues(self.id, status)]

        if not self.isUnstable():
            queries.append(
                'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        return SourcePackagePublishingHistory.select(
            " AND ".join(queries), orderBy="id")

    def getSourcePackagePublishing(self, status, pocket, component=None):
        """See IDistroRelease."""
        orderBy = ['SourcePackageName.name']

        clauseTables = ['SourcePackageRelease', 'SourcePackageName']

        clause = """
            SourcePackagePublishingHistory.sourcepackagerelease=
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename=
                SourcePackageName.id AND
            SourcePackagePublishingHistory.distrorelease=%s AND
            SourcePackagePublishingHistory.status=%s AND
            SourcePackagePublishingHistory.pocket=%s
            """ %  sqlvalues(self.id, status, pocket)

        if component:
            clause += (
                " AND SourcePackagePublishingHistory.component=%s" %
                sqlvalues(component)
                )

        return SourcePackagePublishingHistory.select(
            clause, orderBy=orderBy, clauseTables=clauseTables)

    def getBinaryPackagePublishing(self, name=None, version=None,
                                   archtag=None, sourcename=None,
                                   orderBy=None, pocket=None,
                                   component=None):
        """See IDistroRelease."""

        clauseTables = ['BinaryPackagePublishingHistory', 'DistroArchRelease',
                        'BinaryPackageRelease', 'BinaryPackageName', 'Build',
                        'SourcePackageRelease', 'SourcePackageName' ]

        query = ["""
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id AND
        BinaryPackagePublishingHistory.distroarchrelease =
            DistroArchRelease.id AND
        BinaryPackageRelease.binarypackagename =
            BinaryPackageName.id AND
        BinaryPackageRelease.build =
            Build.id AND
        Build.sourcepackagerelease =
            SourcePackageRelease.id AND
        SourcePackageRelease.sourcepackagename =
            SourcePackageName.id AND
        DistroArchRelease.distrorelease = %s AND
        BinaryPackagePublishingHistory.status = %s
        """ % sqlvalues(self.id, PackagePublishingStatus.PUBLISHED)]

        if name:
            query.append('BinaryPackageName.name = %s' % sqlvalues(name))

        if version:
            query.append('BinaryPackageRelease.version = %s'
                      % sqlvalues(version))

        if archtag:
            query.append('DistroArchRelease.architecturetag = %s'
                      % sqlvalues(archtag))

        if sourcename:
            query.append('SourcePackageName.name = %s' % sqlvalues(sourcename))

        if pocket:
            query.append(
                'BinaryPackagePublishingHistory.pocket = %s'
                % sqlvalues(pocket))

        if component:
            query.append(
                'BinaryPackagePublishingHistory.component = %s'
                % sqlvalues(component))

        query = " AND ".join(query)

        result = BinaryPackagePublishingHistory.select(
            query, distinct=False, clauseTables=clauseTables, orderBy=orderBy)

        return result

    def publishedBinaryPackages(self, component=None):
        """See IDistroRelease."""
        # XXX sabdfl 04/07/05 this can become a utility when that works
        # this is used by the debbugs import process, mkdebwatches
        pubpkgset = getUtility(IPublishedPackageSet)
        result = pubpkgset.query(distrorelease=self, component=component)
        return [BinaryPackageRelease.get(pubrecord.binarypackagerelease)
                for pubrecord in result]

    def getBuildRecords(self, status=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        # find out the distroarchrelease in question
        arch_ids = [arch.id for arch in self.architectures]
        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds(
            arch_ids, status, name, pocket)

    def createUploadedSourcePackageRelease(
        self, sourcepackagename, version, maintainer, builddepends,
        builddependsindep, architecturehintlist, component, creator,
        urgency, changelog, dsc, dscsigningkey, section, manifest,
        dsc_maintainer_rfc822, dsc_standards_version, dsc_format,
        dsc_binaries, dateuploaded=DEFAULT):
        """See IDistroRelease."""
        return SourcePackageRelease(
            uploaddistrorelease=self, sourcepackagename=sourcepackagename,
            version=version, maintainer=maintainer, dateuploaded=dateuploaded,
            builddepends=builddepends, builddependsindep=builddependsindep,
            architecturehintlist=architecturehintlist, component=component,
            creator=creator, urgency=urgency, changelog=changelog, dsc=dsc,
            dscsigningkey=dscsigningkey, section=section, manifest=manifest,
            dsc_maintainer_rfc822=dsc_maintainer_rfc822, dsc_format=dsc_format,
            dsc_standards_version=dsc_standards_version,
            dsc_binaries=dsc_binaries)

    def getComponentByName(self, name):
        """See IDistroRelease."""
        comp = Component.byName(name)
        if comp is None:
            raise NotFoundError(name)
        permitted = set(self.components)
        if comp in permitted:
            return comp
        raise NotFoundError(name)

    def getSectionByName(self, name):
        """See IDistroRelease."""
        section = Section.byName(name)
        if section is None:
            raise NotFoundError(name)
        permitted = set(self.sections)
        if section in permitted:
            return section
        raise NotFoundError(name)

    def removeOldCacheItems(self, log):
        """See IDistroRelease."""

        # get the set of package names that should be there
        bpns = set(BinaryPackageName.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(self, PackagePublishingStatus.REMOVED),
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease',
                          'BinaryPackageRelease']))

        # remove the cache entries for binary packages we no longer want
        for cache in self.binary_package_caches:
            if cache.binarypackagename not in bpns:
                log.debug(
                    "Removing binary cache for '%s' (%s)"
                    % (cache.name, cache.id))
                cache.destroySelf()

    def updateCompletePackageCache(self, log, ztm):
        """See IDistroRelease."""

        # get the set of package names to deal with
        bpns = list(BinaryPackageName.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(self, PackagePublishingStatus.REMOVED),
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease',
                          'BinaryPackageRelease']))

        # now ask each of them to update themselves. commit every 100
        # packages
        counter = 0
        for bpn in bpns:
            log.debug("Considering binary '%s'" % bpn.name)
            self.updatePackageCache(bpn, log)
            counter += 1
            if counter > 99:
                counter = 0
                if ztm is not None:
                    log.debug("Committing")
                    ztm.commit()


    def updatePackageCache(self, binarypackagename, log):
        """See IDistroRelease."""

        # get the set of published binarypackagereleases
        bprs = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishingHistory.binarypackagerelease AND
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(binarypackagename, self,
                            PackagePublishingStatus.REMOVED),
            orderBy='-datecreated',
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease'],
            distinct=True)
        if bprs.count() == 0:
            log.debug("No binary releases found.")
            return

        # find or create the cache entry
        cache = DistroReleasePackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.id, binarypackagename.id))
        if cache is None:
            log.debug("Creating new binary cache entry.")
            cache = DistroReleasePackageCache(
                distrorelease=self,
                binarypackagename=binarypackagename)

        # make sure the cached name, summary and description are correct
        cache.name = binarypackagename.name
        cache.summary = bprs[0].summary
        cache.description = bprs[0].description

        # get the sets of binary package summaries, descriptions. there is
        # likely only one, but just in case...

        summaries = set()
        descriptions = set()
        for bpr in bprs:
            log.debug("Considering binary version %s" % bpr.version)
            summaries.add(bpr.summary)
            descriptions.add(bpr.description)

        # and update the caches
        cache.summaries = ' '.join(sorted(summaries))
        cache.descriptions = ' '.join(sorted(descriptions))

    def searchPackages(self, text):
        """See IDistroRelease."""
        drpcaches = DistroReleasePackageCache.select("""
            distrorelease = %s AND (
            fti @@ ftq(%s) OR
            DistroReleasePackageCache.name ILIKE '%%' || %s || '%%')
            """ % (quote(self.id), quote(text), quote_like(text)),
            selectAlso='rank(fti, ftq(%s)) AS rank' % sqlvalues(text),
            orderBy=['-rank'],
            prejoins=['binarypackagename'],
            distinct=True)
        return [DistroReleaseBinaryPackage(
            distrorelease=self,
            binarypackagename=drpc.binarypackagename) for drpc in drpcaches]

    def newArch(self, architecturetag, processorfamily, official, owner):
        """See IDistroRelease."""
        dar = DistroArchRelease(architecturetag=architecturetag,
            processorfamily=processorfamily, official=official,
            distrorelease=self, owner=owner)
        return dar

    def newMilestone(self, name, dateexpected=None):
        """See IDistroRelease."""
        return Milestone(name=name, dateexpected=dateexpected,
            distribution=self.distribution, distrorelease=self)

    def getLastUploads(self):
        """See IDistroRelease."""
        query = """
        sourcepackagerelease.id=distroreleasequeuesource.sourcepackagerelease
        AND sourcepackagerelease.sourcepackagename=sourcepackagename.id
        AND distroreleasequeuesource.distroreleasequeue=distroreleasequeue.id
        AND distroreleasequeue.status=%s
        AND distroreleasequeue.distrorelease=%s
        """ % sqlvalues(DistroReleaseQueueStatus.DONE, self)

        last_uploads = SourcePackageRelease.select(
            query, limit=5, prejoins=['sourcepackagename'],
            clauseTables=['SourcePackageName', 'DistroReleaseQueue',
                          'DistroReleaseQueueSource'],
            orderBy=['-distroreleasequeue.id'])

        distro_sprs = [
            self.getSourcePackageRelease(spr) for spr in last_uploads]

        return distro_sprs

    def createQueueEntry(self, pocket, changesfilename, changesfilecontent,
                         signing_key=None):
        """See IDistroRelease."""
        # We store the changes file in the librarian to avoid having to
        # deal with broken encodings in these files; this will allow us
        # to regenerate these files as necessary.
        #
        # The use of StringIO here should be safe: we do not encoding of
        # the content in the changes file (as doing so would be guessing
        # at best, causing unpredictable corruption), and simply pass it
        # off to the librarian.
        file_alias_set = getUtility(ILibraryFileAliasSet)
        changes_file = file_alias_set.create(changesfilename,
            len(changesfilecontent), StringIO(changesfilecontent),
            'text/plain')

        return DistroReleaseQueue(
            distrorelease=self, status=DistroReleaseQueueStatus.NEW,
            pocket=pocket, changesfile=changes_file,
            signing_key=signing_key)

    def getPackageUploadQueue(self, state):
        """See IDistroRelease."""
        return PackageUploadQueue(self, state)

    def getQueueItems(self, status=None, name=None, version=None,
                      exact_match=False, pocket=None):
        """See IDistroRelease."""

        default_clauses = ["""
            distroreleasequeue.distrorelease = %s""" % sqlvalues(self.id)]

        # restrict result to a given pocket
        if pocket is not None:
            if not isinstance(pocket, list):
                pocket = [pocket]
            default_clauses.append("""
            distroreleasequeue.pocket IN %s""" % sqlvalues(pocket))

        # XXX cprov 20060606: We may reorganise this code, creating
        # some new methods provided by IDistroReleaseQueueSet, as:
        # getByStatus and getByName.
        if not status:
            assert not version and not exact_match
            return DistroReleaseQueue.select(
                " AND ".join(default_clauses),
                orderBy=['-id'])

        if not isinstance(status, list):
            status = [status]

        default_clauses.append("""
        distroreleasequeue.status IN %s""" % sqlvalues(status))

        if not name:
            assert not version and not exact_match
            return DistroReleaseQueue.select(
                " AND ".join(default_clauses),
                orderBy=['-id'])

        source_where_clauses = default_clauses + ["""
            distroreleasequeue.id = distroreleasequeuesource.distroreleasequeue
            """]

        build_where_clauses = default_clauses + ["""
            distroreleasequeue.id = distroreleasequeuebuild.distroreleasequeue
            """]

        custom_where_clauses = default_clauses + ["""
            distroreleasequeue.id = distroreleasequeuecustom.distroreleasequeue
            """]

        # modify source clause to lookup on sourcepackagerelease
        source_where_clauses.append("""
            distroreleasequeuesource.sourcepackagerelease =
            sourcepackagerelease.id""")
        source_where_clauses.append(
            "sourcepackagerelease.sourcepackagename = sourcepackagename.id")

        # modify build clause to lookup on binarypackagerelease
        build_where_clauses.append(
            "distroreleasequeuebuild.build = binarypackagerelease.build")
        build_where_clauses.append(
            "binarypackagerelease.binarypackagename = binarypackagename.id")

        # modify custom clause to lookup on libraryfilealias
        custom_where_clauses.append(
            "distroreleasequeuecustom.libraryfilealias = "
            "libraryfilealias.id")

        # attempt to exact or similar names in builds, sources and custom
        if exact_match:
            source_where_clauses.append("sourcepackagename.name = '%s'" % name)
            build_where_clauses.append("binarypackagename.name = '%s'" % name)
            custom_where_clauses.append(
                "libraryfilealias.filename='%s'" % name)
        else:
            source_where_clauses.append(
                "sourcepackagename.name LIKE '%%' || %s || '%%'"
                % quote_like(name))

            build_where_clauses.append(
                "binarypackagename.name LIKE '%%' || %s || '%%'"
                % quote_like(name))

            custom_where_clauses.append(
                "libraryfilealias.filename LIKE '%%' || %s || '%%'"
                % quote_like(name))

        # attempt for given version argument, except by custom
        if version:
            # exact or similar matches
            if exact_match:
                source_where_clauses.append(
                    "sourcepackagerelease.version = '%s'" % version)
                build_where_clauses.append(
                    "binarypackagerelease.version = '%s'" % version)
            else:
                source_where_clauses.append(
                    "sourcepackagerelease.version LIKE '%%' || %s || '%%'"
                    % quote_like(version))
                build_where_clauses.append(
                    "binarypackagerelease.version LIKE '%%' || %s || '%%'"
                    % quote_like(version))

        source_clauseTables = [
            'DistroReleaseQueueSource',
            'SourcePackageRelease',
            'SourcePackageName',
            ]
        source_orderBy = ['-sourcepackagerelease.dateuploaded']

        build_clauseTables = [
            'DistroReleaseQueueBuild',
            'BinaryPackageRelease',
            'BinaryPackageName',
            ]
        build_orderBy = ['-binarypackagerelease.datecreated']

        custom_clauseTables = [
            'DistroReleaseQueueCustom',
            'LibraryFileAlias',
            ]
        custom_orderBy = ['-LibraryFileAlias.id']

        source_where_clause = " AND ".join(source_where_clauses)
        source_results = DistroReleaseQueue.select(
            source_where_clause, clauseTables=source_clauseTables,
            orderBy=source_orderBy)

        build_where_clause = " AND ".join(build_where_clauses)
        build_results = DistroReleaseQueue.select(
            build_where_clause, clauseTables=build_clauseTables,
            orderBy=build_orderBy)

        custom_where_clause = " AND ".join(custom_where_clauses)
        custom_results = DistroReleaseQueue.select(
            custom_where_clause, clauseTables=custom_clauseTables,
            orderBy=custom_orderBy)

        return source_results.union(build_results.union(custom_results))

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug on an IDistroRelease,
        # because internally bugs are reported against IDistroRelease only when
        # targetted to be fixed in that release, which is rarely the case for a
        # brand new bug report.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a distribution release, "
            "because releases are meant for \"targeting\" a fix to a specific "
            "release. It's possible that we may change this behaviour to "
            "allow filing a bug on a distribution release in the "
            "not-too-distant future. For now, you probably meant to file "
            "the bug on the distribution instead.")

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.distrorelease = %s' % sqlvalues(self)

    def initialiseFromParent(self):
        """See IDistroRelease."""
        assert self.parentrelease is not None, "Parent release must be present"
        assert SourcePackagePublishingHistory.selectBy(
            distrorelease=self).count() == 0, \
            "Source Publishing must be empty"
        for arch in self.architectures:
            assert BinaryPackagePublishingHistory.selectBy(
                distroarchrelease=arch).count() == 0, \
                "Binary Publishing must be empty"
            try:
                parent_arch = self.parentrelease[arch.architecturetag]
                assert parent_arch.processorfamily == arch.processorfamily, \
                       "The arch tags must match the processor families."
            except KeyError:
                raise AssertionError("Parent release lacks %s" % (
                    arch.architecturetag))
        assert self.nominatedarchindep is not None, \
               "Must have a nominated archindep architecture."
        assert self.components.count() == 0, \
               "Component selections must be empty."
        assert self.sections.count() == 0, \
               "Section selections must be empty."

        # MAINTAINER: dsilvers: 20051031
        # Here we go underneath the SQLObject caching layers in order to
        # generate what will potentially be tens of thousands of rows
        # in various tables. Thus we flush pending updates from the SQLObject
        # layer, perform our work directly in the transaction and then throw
        # the rest of the SQLObject cache away to make sure it hasn't cached
        # anything that is no longer true.

        # Prepare for everything by flushing updates to the database.
        flush_database_updates()
        cur = cursor()

        # Perform the copies
        self._copy_component_and_section_selections(cur)
        self._copy_source_publishing_records(cur)
        for arch in self.architectures:
            parent_arch = self.parentrelease[arch.architecturetag]
            self._copy_binary_publishing_records(cur, arch, parent_arch)
        self._copy_lucille_config(cur)

        # Finally, flush the caches because we've altered stuff behind the
        # back of sqlobject.
        flush_database_caches()

    def _copy_lucille_config(self, cur):
        """Copy all lucille related configuration from our parent release."""
        cur.execute('''
            UPDATE DistroRelease SET lucilleconfig=(
                SELECT pdr.lucilleconfig FROM DistroRelease AS pdr
                WHERE pdr.id = %s)
            WHERE id = %s
            ''' % sqlvalues(self.parentrelease.id, self.id))

    def _copy_binary_publishing_records(self, cur, arch, parent_arch):
        """Copy the binary publishing records from the parent arch release
        to the given arch release in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket.
        """
        cur.execute('''
            INSERT INTO SecureBinaryPackagePublishingHistory (
                binarypackagerelease, distroarchrelease, status,
                component, section, priority, datecreated, datepublished,
                pocket, embargo)
            SELECT bpph.binarypackagerelease, %s as distroarchrelease,
                   bpph.status, bpph.component, bpph.section, bpph.priority,
                   %s as datecreated, %s as datepublished, %s as pocket,
                   false as embargo
            FROM BinaryPackagePublishingHistory AS bpph
            WHERE bpph.distroarchrelease = %s AND bpph.status in (%s, %s) AND
                  bpph.pocket = %s
            ''' % sqlvalues(arch.id, UTC_NOW, UTC_NOW,
                            PackagePublishingPocket.RELEASE,
                            parent_arch.id,
                            PackagePublishingStatus.PENDING,
                            PackagePublishingStatus.PUBLISHED,
                            PackagePublishingPocket.RELEASE))

    def _copy_source_publishing_records(self, cur):
        """Copy the source publishing records from our parent distro release.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket.
        """
        cur.execute('''
            INSERT INTO SecureSourcePackagePublishingHistory (
                sourcepackagerelease, distrorelease, status, component,
                section, datecreated, datepublished, pocket, embargo)
            SELECT spph.sourcepackagerelease, %s as distrorelease,
                   spph.status, spph.component, spph.section,
                   %s as datecreated, %s as datepublished,
                   %s as pocket, false as embargo
            FROM SourcePackagePublishingHistory AS spph
            WHERE spph.distrorelease = %s AND spph.status in (%s, %s) AND
                  spph.pocket = %s
            ''' % sqlvalues(self.id, UTC_NOW, UTC_NOW,
                            PackagePublishingPocket.RELEASE,
                            self.parentrelease.id,
                            PackagePublishingStatus.PENDING,
                            PackagePublishingStatus.PUBLISHED,
                            PackagePublishingPocket.RELEASE))

    def _copy_component_and_section_selections(self, cur):
        """Copy the section and component selections from the parent distro
        release into this one.
        """
        # Copy the component selections
        cur.execute('''
            INSERT INTO ComponentSelection (distrorelease, component)
            SELECT %s AS distrorelease, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentrelease.id))
        # Copy the section selections
        cur.execute('''
            INSERT INTO SectionSelection (distrorelease, section)
            SELECT %s as distrorelease, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentrelease.id))


    def _holding_table_unquoted(self, tablename, suffix=''):
        """Name for a holding table, but without quotes.  Use with care."""
        if suffix:
            suffix = '_%s' % suffix
        return "%s_holding_%s%s" % (str(tablename), str(self.name), suffix)

    def _holding_table(self, tablename, suffix=''):
        """Name for a holding table to hold data being copied in tablename.

        This is used to copy translation data from the parent distrorelease to
        self.  To reduce locking on the database, applicable data is first
        copied to these holding tables, then modified there, and finally moved
        back into the original table "tablename."

        Return value is properly quoted for use as an SQL identifier.
        """
        return str(
            quoteIdentifier(self._holding_table_unquoted(tablename, suffix)))


    def _extract_to_holding_table(self,
            ztm,
            logger,
            orgtable,
            joins=[],
            whereclause=None,
            idseq=None):
        """Extract (selected) rows from orgtable into a holding table.

        This is used to copy a distrorelease's current translation elements to
        a new distrorelease.  The idea is that all translation data can be
        copied into holding tables first (without starving other users of
        database service through excessive locking), and provided with new
        row ids so they can be directly re-inserted into the original tables.

        A new table is created and filled with any records from orgtable that
        match filtering criteria passed in whereclause.  The new table's name
        is constructed as self._holding_table(orgtable).  If a table of that
        name already existed, it is dropped first.

        The new table gets an additional new_id column with identifiers in the
        seqid sequence; the name seqid defaults to the original table name in
        lower case, with "_seq_id" appended.  Apart from this extra column,
        indexes, and constraints, the holding table is schematically identical
        to orgtable.  A unique index is created for the original id column.

        There is a special facility for redirecting foreign keys to other
        tables copied in the same way.  If the joins argument is a nonempty
        list, the selection used in creating the new table  will be joined
        with each of the tables named in joins, on foreign keys in the current
        table.  The foreign keys in the holding table will point to the
        new_ids of the copied rows, rather than the original ids.  Rows in
        orgtable will only be copied to their holding table if all rows they
        are joined with in those other tables were also copied to holding
        tables of their own.

        The foreign keys are assumed to have the same names as the tables
        they refer to, but written in lower-case letters.

        When joining, the added tables' columns are not included in the
        holding table, but whereclause may select on them.
        """
        if idseq is None:
            idseq = "%s_id_seq" % orgtable.lower()

        holding = self._holding_table(orgtable)

        logger.info('Extracting from %s into %s...' % (orgtable,holding))

        starttime = time.time()

        # Selection clauses for our foreign keys
        new_fks = [
            "%s.new_id AS new_%s" % (self._holding_table(j), j.lower())
            for j in joins
        ]

        # Combined "where" clauses
        where = [
            "%s = %s.id" % (j.lower(), self._holding_table(j))
            for j in joins
        ]
        if whereclause is not None:
            where = where + ['(%s)'%whereclause]

        cur = cursor()

        # We use a regular, persistent table rather than a temp table for
        # this so that we get a chance to resume interrupted copies, and
        # analyse failures.  If we used temp tables, they'd be gone by the
        # time we knew something went wrong.
        # For each row we append at the end any new foreign key values, and
        # finally a "new_id" holding its future id field.  This new_id value
        # is allocated from the original table's id sequence, so it will be
        # unique in the original table.
        cur.execute('''
            CREATE TABLE %s AS
            SELECT %s, nextval('%s'::regclass) AS new_id
            FROM %s
            WHERE %s
        ''' % (holding,
            ', '.join(['%s.*'%orgtable] + new_fks),
            idseq,
            ', '.join([orgtable] +
                ['%s'%self._holding_table(j) for j in joins]),
            ' AND '.join(where)))

        if joins:
            # Replace foreign keys with their "new_" variants, then drop those
            # "new_" columns we added.
            fkupdates = [
                "%s = new_%s" % (j.lower(),j.lower()) for j in joins
            ]
            updatestr = ', '.join(fkupdates)
            logger.info("Redirecting foreign keys: %s" % updatestr)
            cur.execute('''
                UPDATE %s
                SET %s
            ''' % (holding, updatestr))
            for j in joins:
                column = j.lower()
                logger.info("Dropping foreign-key column %s" % column)
                cur.execute('''
                    ALTER TABLE %s DROP COLUMN new_%s
                ''' % (holding, column))

        # Now that our new holding table is in a stable state, index its id
        logger.info("Indexing %s" % holding)
        cur.execute('''
            CREATE UNIQUE INDEX %s
            ON %s (id)
        ''' % (self._holding_table(orgtable, 'id'), holding))
        logger.info('...Extracted in %f seconds' % (time.time()-starttime))


    # These are the tables that need data to be copied when a new
    # distrorelease is opened for translation.  The order matters to several
    # methods.
    # Ordering of this list is significant for two reasons:
    # 1. To maintain referential integrity while pouring--we can't insert
    #    a row into a source table if it has a foreign key matched up with
    #    another row in another table that hasn't been poured yet.
    # 2. The _recoverable_holding_tables() method must know what the first
    #    and last tables in this list are, so it can correctly detect the
    #    state of any previous pouring run that may have been interrupted.
    _translation_tables = [
        'POTemplate', 'POTMsgSet', 'POMsgIDSighting', 'POFile',
        'POMsgSet', 'POSubmission'
    ]

    def _recoverable_holding_tables(self, logger):
        """Do we have holding tables with recoverable data from previous run?
        """
        # The tables named here are the first and last tables in the list that
        # _pour_holding_tables() goes through.  Keep it that way, or this will
        # return incorrect information!

        cur = cursor()

        # If there are any holding tables to be poured into their source
        # tables, there must at least be one for the last table that
        # _pour_holding_tables() processes.
        if not postgresql.haveTable(cur,
                self._holding_table_unquoted(self._translation_tables[-1])):
            return False

        # If the first table in our list also still exists, and it still has
        # its new_id column, then the pouring process had not begun yet.
        # Assume the data was not ready for pouring.
        if postgresql.tableHasColumn(cur,
                self._holding_table_unquoted(self._translation_tables[0]),
                'new_id'):
            logger.info(
                "Previous run aborted too early for recovery; redo all")
            return False

        logger.info("Recoverable data found")
        return True


    def _pour_holding_tables(self, logger, ztm):
        """Attempt to pour translation holding tables back into source tables.

        ztm is committed and re-opened at the beginning of each run.  This is
        done so the caller still has a chance to play atomically with the
        holding table's data.
        """
        if ztm is not None:
            commitstart = time.time()
            ztm.commit()
            logger.info("Committed in %f seconds" % (time.time()-commitstart))
            ztm.begin()

        cur = cursor()

        # Main loop: for each of the source tables involved in copying
        # translations from our parent distrorelease, see if there's a
        # matching holding table; prepare it, pour it back into the source
        # table, and drop.
        for table in self._translation_tables:
            holding = self._holding_table(table)
            rawholding = self._holding_table_unquoted(table)

            if not postgresql.haveTable(cur, rawholding):
                # We know we're in a suitable state for pouring.  If this
                # table does not exist, it must be because it's been poured
                # out completely and dropped in an earlier instance of this
                # loop, before the failure we're apparently recovering from.
                continue

            # XXX: JeroenVermeulen 2007-05-02, Lock holding table maybe, to
            # protect against accidental concurrent runs?
            logger.info("Pouring %s back into %s..." % (holding,table))

            tablestarttime = time.time()

            if postgresql.tableHasColumn(cur, rawholding, 'new_id'):
                # Update ids in holding table from originals to copies.
                # (If this is where we got interrupted by a failure in a
                # previous run, no harm in doing it again)
                cur.execute("UPDATE %s SET id=new_id" % holding)
                # Restore table to original schema
                cur.execute("ALTER TABLE %s DROP COLUMN new_id" % holding)
                logger.info("...rearranged ids in %f seconds..." %
                    (time.time()-tablestarttime))

            # Now pour holding table's data into its source table.  This is
            # where we start writing to tables that other clients will be
            # reading, so row locks are a concern.  Break the writes up in
            # batches of a few thousand rows.  The goal is to have these
            # transactions running no longer than five seconds or so each.

            # We batch simply by breaking the range of ids in our table down
            # into fixed-size intervals.  Some of those fixed-size intervals
            # may not have any rows in them, or very few.  That's not likely
            # to be a problem though since we allocated all these ids in one
            # single SQL statement.  No time for gaps to form.
            cur.execute("SELECT min(id), max(id) FROM %s" % holding)
            bounds = cur.fetchall()[0]
            lowest = bounds[0]
            highest = bounds[1]
            total_rows = highest + 1 - lowest
            logger.info("Up to %d rows in holding table" % total_rows)

            if ztm is not None:
                precommitstart = time.time()
                ztm.commit()
                logger.info("...pre-commit in %f seconds..." % (
                    time.time() - precommitstart))
                ztm.begin()
                cur = cursor()

            # Minimum batch size.  We never process fewer rows than this in
            # one batch because at that level, we expect to be running into
            # more or less constant transaction costs.  Reducing batch size
            # any further is not likely to help much, but will make the
            # overall procedure take much longer.
            min_batch_size = 1000

            # The number of seconds we want each transaction to take.  The
            # batching algorithm tries to approximate this batch time by
            # varying actual batch_size.
            time_goal = 4

            # When's the last time we re-generated statistics on our id
            # column?  When that information stales, performance degrades very
            # suddenly and very dramatically.
            deletions_since_analyze = 0
            batches_since_analyze = 0

            batch_size = min_batch_size
            while lowest <= highest:
                # Step through ids backwards.  This appears to be faster,
                # possibly because we're removing records from the end of the
                # table instead of from the beginning, or perhaps it makes
                # rebalancing the index a bit easier.
                next = highest - batch_size
                logger.info("Moving %d ids: %d-%d..." % (
                    highest-next, next, highest))
                batchstarttime = time.time()

                cur.execute('''
                    INSERT INTO %s (
                        SELECT *
                        FROM %s
                        WHERE id >= %d
                    )''' % (table, holding, next))
                cur.execute('''
                    DELETE FROM %s
                    WHERE id >= %d
                ''' % (holding, next))

                deletions_since_analyze = deletions_since_analyze + batch_size

                if ztm is not None:
                    ztm.commit()
                    ztm.begin()
                    cur = cursor()

                highest = next

                time_taken = time.time() - batchstarttime
                logger.info("...batch done in %f seconds (%d%%)." % (
                    time_taken, 100*(total_rows+lowest-highest)/total_rows))


                # Adjust batch_size to approximate time_goal.  The new
                # batch_size is the average of two values: the previous value
                # for batch_size, and an estimate of how many rows would take
                # us to exactly time_goal seconds.  The estimate is very
                # simple: rows per second on the last commit.  We get
                # exponential decay of speed history, with an exponent of 1/2.
                # Set a reasonable minimum for time_taken, just in case we get
                # weird values for whatever reason and destabilize the
                # algorithm.
                time_taken = max(time_goal/10, time_taken)
                batch_size = batch_size*(1 + time_goal/time_taken)/2

                # When the server's statistics on our id column stale,
                # performance drops suddenly and dramatically as postgres
                # stops using our primary key index and starts doing
                # sequential scans.  A quick "ANALYZE" run should fix that.
                # Doesn't take long, either, so we try to do it before the
                # problem occurs.
                # Re-analyze periodically just in case; plus when performance
                # drops and forces batch_size down to its minimum value; and
                # whenever we've deleted about a fifth of our remaining rows
                # since our last run.  Disaster seems to strike around
                # one-third, even when there are only a hundred thousand or so
                # rows left.  Don't analyze too often if something else is
                # forcing performance down, though.
                if batches_since_analyze > 3 and (
                        batch_size < min_batch_size or
                        deletions_since_analyze > 1000000 or
                        (highest-lowest)/5 < deletions_since_analyze):
                    analyzestarttime = time.time()
                    cur.execute("ANALYZE %s (id)" % holding)
                    logger.info("Analyzed in %f seconds" % (
                        time.time() - analyzestarttime))
                    deletions_since_analyze = 0
                    batches_sinze_analyze = 0

                batch_size = max(batch_size, min_batch_size)
                batches_since_analyze = batches_since_analyze + 1

            logger.info(
                "Pouring %s took %f seconds." %
                    (holding,time.time()-tablestarttime))

            dropstart = time.time()
            cur.execute("DROP TABLE %s" % holding)
            logger.info("Dropped %s in %f seconds" % (
                holding, time.time() - dropstart))


    def _copy_active_translations_to_new_release(self, logger, ztm):
        """We're a new release; inherit translations from parent.

        Translation data for the new release (self) is first copied into
        "holding tables" with names like "POTemplate_tmp_feisty_271" and
        processed there.  Then, at the end of the procedure, these tables are
        all copied back to their originals.

        If this procedure fails, it may leave holding tables behind.  This was
        done deliberately to leave some forensics information for failures,
        and also to allow admins to see what data has and has not been copied.

        The holding tables have names like "POTemplate_holding_feisty" (for
        source table POTemplate and release feisty, in this case).

        If a holding table left behind by an abortive run has a column called
        new_id at the end, it contains unfinished data and may as well be
        dropped.  If it does not have that column, the holding table was
        already in the process of being copied back to its origin table.  In
        that case the sensible thing to do is probably to continue copying it.
        """

        # This method was extracted as one of two cases from a huge
        # _copy_active_translations() method.  Because it only deals with the
        # case where "self" is a new release without any existing translations
        # attached, it can afford to be much more cavalier with ACID
        # considerations than the other case can.  Still, it may be possible
        # in the future to optimize _copy_active_translations_as_update() (the
        # other of the two cases) using a similar trick.

        # Copying happens in two phases:
        #
        # 1. Extraction phase--for every table involved (which we'll call a
        # "source table" here), we create a "holding table."  We fill that with
        # all rows from the source table that we want to copy from the parent
        # release.  We make some changes to the copied rows, such as making
        # them belong to ourselves instead of our parent release.
        #
        # The first phase does not modify any tables that other clients may
        # want to use, avoiding locking problems.
        #
        # 2. Pouring phase.  From each holding table we pour all rows back
        # into the source table, deleting them from the holding table as we
        # go.  The holding table is dropped once empty.
        #
        # The second phase is "batched," moving only a small number of rows at
        # a time, then performing an intermediate commit.  This avoids holding
        # too many locks for too long and disrupting regular database service.

        # A unique suffix we will use for names of holding tables.  We don't
        # use proper SQL holding tables because those will have disappeared
        # whenever admins want to analyze a failure, figure out how far this
        # function got in copying data, or resume after failure.

        # Clean up any remains from a previous run.  If we got here, that
        # means those remains are not salvagable.

        postgresql.dropTables(cursor(),
            [self._holding_table(t) for t in self._translation_tables])

        # Copy relevant POTemplates from existing release into a holding
        # table, complete with their original id fields.
        self._extract_to_holding_table(ztm,
            logger,
            'POTemplate',
            [],
            'distrorelease=%s AND iscurrent' % quote(self.parentrelease))

        # Now that we have the data "in private," where nobody else can see
        # it, we're free to play with it.  No risk of locking other processes
        # out of the database.
        # Update release names in the holding table (right now they all bear
        # our parent's name) to our own name, and set creation dates to now.
        cursor().execute('''
            UPDATE %s
            SET
                distrorelease = %s,
                datecreated =
                    timezone('UTC'::text,
                        ('now'::text)::timestamp(6) with time zone)
        ''' % (self._holding_table('POTemplate'), quote(self)))


        # Copy each POTMsgSet whose template we copied, and replace each
        # potemplate reference with a reference to our copy of the original
        # POTMsgSet's potemplate.
        self._extract_to_holding_table(ztm,
            logger,
            'POTMsgSet',
            ['POTemplate'],
            'POTMsgSet.sequence > 0')

        # Copy POMsgIDSightings, substituting their potmsgset foreign
        # keys with references to our own, copied POTMsgSets
        self._extract_to_holding_table(ztm,
            logger,
            'POMsgIDSighting',
            ['POTMsgSet'])

        # Copy POFiles, making them refer to our copied POTemplates
        self._extract_to_holding_table(ztm,
            logger,
            'POFile',
            ['POTemplate'])

        # Same for POMsgSet, but a bit more complicated since it refers to
        # both POFile and POTMsgSet.
        self._extract_to_holding_table(ztm,
            logger,
            'POMsgSet',
            ['POFile', 'POTMsgSet'])

        # And for POSubmission
        self._extract_to_holding_table(ztm,
            logger,
            'POSubmission',
            ['POMsgSet'],
            'active OR published')

        # Now pour the holding tables back into the originals
        self._pour_holding_tables(logger, ztm)


    def _copy_active_translations_as_update(self, logger):
        """Receive active, updated translations from parent release.
        """

        # This method was extracted as one of two cases from a huge
        # _copy_active_translations() method.  It's likely to cause problems
        # to other users while running, locking them out of the database
        # during its potentially huge updates.  We should see if we can batch
        # it into smaller chunks in order to reduce lock pressure.

        # XXX: JeroenVermeulen 2007-05-03, This method should become
        # unnecessary once the "translation multicast" spec is implemented:
        # https://launchpad.canonical.com/MulticastTranslations

        # The left outer join that obtains pf2 ensures that we only do the
        # copying for POFiles whose POTemplates don't have any POFiles yet.

        # XXX: JeroenVermeulen 2007-04-27, We must be careful when batching
        # this statement.  After one POFile is copied, pt2 will have a POFile
        # attached and its other POFiles will no longer qualify for copying.

        logger.info('Filling POFile table...')
        cur = cursor()
        cur.execute('''
            INSERT INTO POFile (
                potemplate, language, description, topcomment, header,
                fuzzyheader, lasttranslator, currentcount, updatescount,
                rosettacount, lastparsed, owner, variant, path, exportfile,
                exporttime, datecreated, last_touched_pomsgset,
                from_sourcepackagename)
            SELECT
                pt2.id AS potemplate,
                pf1.language AS language,
                pf1.description AS description,
                pf1.topcomment AS topcomment,
                pf1.header AS header,
                pf1.fuzzyheader AS fuzzyheader,
                pf1.lasttranslator AS lasttranslator,
                pf1.currentcount AS currentcount,
                pf1.updatescount AS updatescount,
                pf1.rosettacount AS rosettacount,
                pf1.lastparsed AS lastparsed,
                pf1.owner AS owner,
                pf1.variant AS variant,
                pf1.path AS path,
                pf1.exportfile AS exportfile,
                pf1.exporttime AS exporttime,
                pf1.datecreated AS datecreated,
                pf1.last_touched_pomsgset AS last_touched_pomsgset,
                pf1.from_sourcepackagename AS from_sourcepackagename
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.sourcepackagename = pt1.sourcepackagename AND
                    pt2.distrorelease = %s
                LEFT OUTER JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
            WHERE
                pt1.distrorelease = %s AND
                pf2.id IS NULL''' % sqlvalues(self, self.parentrelease))

        logger.info('Updating POMsgSet table...')
        cur.execute('''
            UPDATE POMsgSet SET
                iscomplete = pms1.iscomplete, isfuzzy = pms1.isfuzzy,
                isupdated = pms1.isupdated,
                reviewer = pms1.reviewer,
                date_reviewed = pms1.date_reviewed
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.sourcepackagename = pt1.sourcepackagename AND
                    pt2.distrorelease = %s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
            WHERE
                pt1.distrorelease = %s AND
                POMsgSet.potmsgset = ptms2.id AND
                POMsgSet.pofile = pf2.id AND
                POMsgSet.iscomplete = FALSE AND
                pms1.iscomplete = TRUE
                ''' % sqlvalues(self, self.parentrelease))

        logger.info('Filling POMsgSet table...')
        cur.execute('''
            INSERT INTO POMsgSet (
                sequence, pofile, iscomplete, obsolete, isfuzzy, commenttext,
                potmsgset, publishedfuzzy, publishedcomplete, isupdated)
            SELECT
                pms1.sequence AS sequence,
                pf2.id AS pofile,
                pms1.iscomplete AS iscomplete,
                pms1.obsolete AS obsolete,
                pms1.isfuzzy AS isfuzzy,
                pms1.commenttext AS commenttext,
                ptms2.id AS potmsgset,
                pms1.publishedfuzzy AS publishedfuzzy,
                pms1.publishedcomplete AS publishedcomplete,
                pms1.isupdated AS isupdated
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.sourcepackagename = pt1.sourcepackagename AND
                    pt2.distrorelease = %s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                LEFT OUTER JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.pofile = pf2.id
            WHERE
                pt1.distrorelease = %s AND
                pms2.id IS NULL''' % sqlvalues(self, self.parentrelease))

        # At this point, we need to know the list of POFiles that we are
        # going to modify so we can recalculate later its statistics. We
        # do this before copying POSubmission table entries because
        # otherwise we will not know exactly which one are being updated.
        logger.info('Getting the list of POFiles with changes...')
        cur.execute('''
            SELECT
                DISTINCT pf2.id
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.sourcepackagename = pt1.sourcepackagename AND
                    pt2.distrorelease = %s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.pofile = pf2.id
                JOIN POSubmission AS ps1 ON
                    ps1.pomsgset = pms1.id AND
                    ps1.active
                LEFT OUTER JOIN POSubmission AS ps2 ON
                    ps2.pomsgset = pms2.id AND
                    ps2.pluralform = ps1.pluralform AND
                    ps2.potranslation = ps1.potranslation AND
                    ((ps2.published AND ps2.active) OR ps2.active = FALSE)
            WHERE
                pt1.distrorelease = %s AND ps2.id IS NULL
                ''' % sqlvalues(self, self.parentrelease))

        pofile_rows = cur.fetchall()
        pofile_ids = [row[0] for row in pofile_rows]

        replacements = sqlvalues(
            release=self, parentrelease=self.parentrelease)

        logger.info( 'Filling POSubmission table with active rows...')
        replacements['published'] = u'FALSE'
        replacements['active'] = u'FALSE'

        cur.execute('''
            INSERT INTO POSubmission (
                pomsgset, pluralform, potranslation, origin, datecreated,
                person, validationstatus, active, published)
            SELECT
                pms2.id AS pomsgset,
                ps1.pluralform AS pluralform,
                ps1.potranslation AS potranslation,
                ps1.origin AS origin,
                ps1.datecreated AS datecreated,
                ps1.person AS person,
                ps1.validationstatus AS validationstatus,
                %(active)s,
                %(published)s
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.sourcepackagename = pt1.sourcepackagename AND
                    pt2.distrorelease = %(release)s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.pofile = pf2.id
                JOIN POSubmission AS ps1 ON
                    ps1.pomsgset = pms1.id AND
                    (ps1.active OR %(published)s)
                LEFT OUTER JOIN POSubmission AS ps2 ON
                    ps2.pomsgset = pms2.id AND
                    ps2.pluralform = ps1.pluralform AND
                    ps2.potranslation = ps1.potranslation
            WHERE
                pt1.distrorelease = %(parentrelease)s AND ps2.id IS NULL
            ''' % replacements)

        # This query will be only useful if when we already have some
        # initial translations before this method call, because is the
        # only situation when we could have POSubmission rows to update.
        logger.info(
            'Updating previous existing POSubmission rows...')
        cur.execute('''
            UPDATE POSubmission
                SET active = FALSE
                FROM
                    POTemplate AS pt1
                    JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                    JOIN POTemplate AS pt2 ON
                        pt2.potemplatename = pt1.potemplatename AND
                        pt2.sourcepackagename = pt1.sourcepackagename AND
                        pt2.distrorelease = %s
                    JOIN POFile AS pf2 ON
                        pf2.potemplate = pt2.id AND
                        pf2.language = pf1.language AND
                        (pf2.variant = pf1.variant OR
                         (pf2.variant IS NULL AND pf1.variant IS NULL))
                    JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                    JOIN POMsgSet AS pms1 ON
                        pms1.potmsgset = ptms1.id AND
                        pms1.pofile = pf1.id AND
                        pms1.iscomplete = TRUE
                    JOIN POTMsgSet AS ptms2 ON
                        ptms2.potemplate = pt2.id AND
                        ptms2.primemsgid = ptms1.primemsgid
                    JOIN POMsgSet AS pms2 ON
                        pms2.potmsgset = ptms2.id AND
                        pms2.pofile = pf2.id
                    JOIN POSubmission AS ps1 ON
                        ps1.pomsgset = pms1.id AND
                        ps1.active
                    LEFT JOIN POSubmission AS newactive_ps2 ON
                        newactive_ps2.pomsgset = pms2.id AND
                        newactive_ps2.pluralform = ps1.pluralform AND
                        newactive_ps2.potranslation = ps1.potranslation
                WHERE
                    pt1.distrorelease = %s AND
                    POSubmission.pomsgset = pms2.id AND
                    POSubmission.pluralform = ps1.pluralform AND
                    POSubmission.potranslation <> ps1.potranslation AND
                    POSubmission.active AND POSubmission.published AND
                    newactive_ps2 IS NOT NULL
                ''' % sqlvalues(self, self.parentrelease))

        cur.execute('''
            UPDATE POSubmission
                SET active = TRUE
                FROM
                    POTemplate AS pt1
                    JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                    JOIN POTemplate AS pt2 ON
                        pt2.potemplatename = pt1.potemplatename AND
                        pt2.sourcepackagename = pt1.sourcepackagename AND
                        pt2.distrorelease = %s
                    JOIN POFile AS pf2 ON
                        pf2.potemplate = pt2.id AND
                        pf2.language = pf1.language AND
                        (pf2.variant = pf1.variant OR
                         (pf2.variant IS NULL AND pf1.variant IS NULL))
                    JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                    JOIN POMsgSet AS pms1 ON
                        pms1.potmsgset = ptms1.id AND
                        pms1.pofile = pf1.id AND
                        pms1.iscomplete = TRUE
                    JOIN POTMsgSet AS ptms2 ON
                        ptms2.potemplate = pt2.id AND
                        ptms2.primemsgid = ptms1.primemsgid
                    JOIN POMsgSet AS pms2 ON
                        pms2.potmsgset = ptms2.id AND
                        pms2.pofile = pf2.id
                    JOIN POSubmission AS ps1 ON
                        ps1.pomsgset = pms1.id AND
                        ps1.active
                    LEFT JOIN POSubmission AS active_ps2 ON
                        active_ps2.pomsgset = pms2.id AND
                        active_ps2.pluralform = ps1.pluralform AND
                        active_ps2.active
                WHERE
                    pt1.distrorelease = %s AND
                    POSubmission.pomsgset = pms2.id AND
                    POSubmission.pluralform = ps1.pluralform AND
                    POSubmission.potranslation = ps1.potranslation AND
                    NOT POSubmission.active AND
                    active_ps2 IS NULL
                ''' % sqlvalues(self, self.parentrelease))

        # Update the statistics cache for every POFile we touched.
        logger.info("Updating POFile's statistics")
        for pofile_id in pofile_ids:
            pofile = POFile.get(pofile_id)
            pofile.updateStatistics()


    def _copy_active_translations(self, ztm):
        """Copy active translations from the parent into this one.

        This method is used in two scenarios: when a new distribution release
        is opened for translation, and during periodic updates as new
        translations from the parent release are ported to newer releases that
        haven't provided translations of their own for the same strings yet.
        In the former scenario a full copy is drawn from the parent release.

        If this distrorelease doesn't have any translatable resource, this
        method will clone all of the parent's current translatable resources;
        otherwise, only the translations that are in the parent but lacking in
        this one will be copied.

        If there is a status change but no translation is changed for a given
        message, we don't have a way to figure whether the change was done in
        the parent or this distrorelease, so we don't migrate that.
        """
        if self.parent is None:
            # We don't have a parent from where we could copy translations.
            return

        logger = logging.getLogger('initialise')

        if len(self.potemplates) == 0:
            # We're a new distrorelease; copy from scratch
            self._copy_active_translations_to_new_release(logger, ztm)
        elif self._recoverable_holding_tables(logger):
            # Recover data from previous, abortive run
            self._pour_holding_tables(logger, ztm)
        else:
            # Incremental copy of updates from parent distrorelease
            self._copy_active_translations_as_update(logger)


    def copyMissingTranslationsFromParent(self, ztm=None):
        """See IDistroRelease."""
        flush_database_updates()
        flush_database_caches()
        # Request the translation copy.
        self._copy_active_translations(ztm)

    def getPendingPublications(self, pocket, is_careful):
        """See IPublishing."""
        queries = ['distrorelease = %s' % sqlvalues(self)]
        # careful publishing should include all PUBLISHED rows, normal run
        # only includes PENDING ones.
        statuses = [PackagePublishingStatus.PENDING]
        if is_careful:
            statuses.append(PackagePublishingStatus.PUBLISHED)
        queries.append('status IN %s' % sqlvalues(statuses))

        # restrict to a specific pocket.
        queries.append('pocket = %s' % sqlvalues(pocket))

        # exclude RELEASE pocket if the distrorelease was already released,
        # since it should not change.
        if not self.isUnstable():
            queries.append(
            'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        publications = SourcePackagePublishingHistory.select(
            " AND ".join(queries), orderBy="-id")

        return publications

    def publish(self, diskpool, log, pocket, is_careful=False):
        """See IPublishing."""
        log.debug("Publishing %s-%s" % (self.title, pocket.name))
        log.debug("Attempting to publish pending sources.")

        dirty_pockets = set()
        for spph in self.getPendingPublications(pocket, is_careful):
            if not is_careful and self.checkLegalPocket(spph, log):
                continue
            spph.publish(diskpool, log)
            dirty_pockets.add((self.name, spph.pocket))

        # propagate publication request to each distroarchrelease.
        for dar in self.architectures:
            more_dirt = dar.publish(diskpool, log, pocket, is_careful)
            dirty_pockets.update(more_dirt)

        return dirty_pockets

    def checkLegalPocket(self, publication, log):
        # If we're not republishing, we want to make sure that
        # we're not publishing packages into the wrong pocket.
        # Unfortunately for careful mode that can't hold true
        # because we indeed need to republish everything.
        if (self.isUnstable() and
            publication.pocket != PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into a non-release "
                      "pocket on unstable release %s, skipping" %
                      (publication.displayname, publication.id, 
                       self.displayname))
            return True
        if (not self.isUnstable() and
            publication.pocket == PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into release pocket "
                      "on stable release %s, skipping" %
                      (publication.displayname, publication.id,
                       self.displayname))
            return True
        return False


class DistroReleaseSet:
    implements(IDistroReleaseSet)

    def get(self, distroreleaseid):
        """See IDistroReleaseSet."""
        return DistroRelease.get(distroreleaseid)

    def translatables(self):
        """See IDistroReleaseSet."""
        return DistroRelease.select(
            "POTemplate.distrorelease=DistroRelease.id",
            clauseTables=['POTemplate'], distinct=True)

    def findByName(self, name):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(name=name)

    def queryByName(self, distribution, name):
        """See IDistroReleaseSet."""
        return DistroRelease.selectOneBy(distribution=distribution, name=name)

    def findByVersion(self, version):
        """See IDistroReleaseSet."""
        return DistroRelease.selectBy(version=version)

    def search(self, distribution=None, isreleased=None, orderBy=None):
        """See IDistroReleaseSet."""
        where_clause = ""
        if distribution is not None:
            where_clause += "distribution = %s" % sqlvalues(distribution.id)
        if isreleased is not None:
            if where_clause:
                where_clause += " AND "
            if isreleased:
                # The query is filtered on released releases.
                where_clause += "releasestatus in (%s, %s)" % sqlvalues(
                    DistributionReleaseStatus.CURRENT,
                    DistributionReleaseStatus.SUPPORTED)
            else:
                # The query is filtered on unreleased releases.
                where_clause += "releasestatus in (%s, %s, %s)" % sqlvalues(
                    DistributionReleaseStatus.EXPERIMENTAL,
                    DistributionReleaseStatus.DEVELOPMENT,
                    DistributionReleaseStatus.FROZEN)
        if orderBy is not None:
            return DistroRelease.select(where_clause, orderBy=orderBy)
        else:
            return DistroRelease.select(where_clause)

    def new(self, distribution, name, displayname, title, summary, description,
            version, parentrelease, owner):
        """See IDistroReleaseSet."""
        return DistroRelease(
            distribution=distribution,
            name=name,
            displayname=displayname,
            title=title,
            summary=summary,
            description=description,
            version=version,
            releasestatus=DistributionReleaseStatus.EXPERIMENTAL,
            parentrelease=parentrelease,
            owner=owner)

