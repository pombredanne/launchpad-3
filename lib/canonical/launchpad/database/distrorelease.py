# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution release."""

__metaclass__ = type

__all__ = [
    'DistroRelease',
    'DistroReleaseSet',
    ]

from cStringIO import StringIO

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, SQLMultipleJoin, IntCol, SQLObjectNotFound,
    SQLRelatedJoin)

from canonical.cachedproperty import cachedproperty

from canonical.database.sqlbase import (quote_like, quote, SQLBase,
    sqlvalues, flush_database_updates, cursor, flush_database_caches)
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.lp.dbschema import (
    PackagePublishingStatus, EnumCol, DistributionReleaseStatus,
    DistroReleaseQueueStatus, PackagePublishingPocket, SpecificationSort,
    SpecificationGoalStatus, SpecificationFilter)

from canonical.launchpad.interfaces import (
    IDistroRelease, IDistroReleaseSet, ISourcePackageName,
    IPublishedPackageSet, IHasBuildRecords, NotFoundError,
    IBinaryPackageName, ILibraryFileAliasSet, IBuildSet,
    ISourcePackage, ISourcePackageNameSet, IHasQueueItems)

from canonical.launchpad.components.bugtarget import BugTargetBase
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.distroreleasebinarypackage import (
    DistroReleaseBinaryPackage)
from canonical.launchpad.database.distroreleasesourcepackagerelease import (
    DistroReleaseSourcePackageRelease)
from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache)
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.publishing import (
    SourcePackagePublishing, BinaryPackagePublishing,
    BinaryPackagePublishingHistory, SourcePackagePublishingHistory)
from canonical.launchpad.database.distroarchrelease import DistroArchRelease
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.cve import CveSet
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
from canonical.launchpad.database.specification import Specification
from canonical.launchpad.database.queue import DistroReleaseQueue
from canonical.launchpad.helpers import shortlist


class DistroRelease(SQLBase, BugTargetBase):
    """A particular release of a distribution."""
    implements(IDistroRelease, IHasBuildRecords, IHasQueueItems)

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

    milestones = SQLMultipleJoin('Milestone', joinColumn = 'distrorelease',
                            orderBy=['dateexpected', 'name'])
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

    @property
    def status(self):
        return self.releasestatus.title

    def canUploadToPocket(self, pocket):
        """See IDistroRelease."""
        # frozen/released states
        released_states = [
            DistributionReleaseStatus.FROZEN,
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
            SourcePackagePublishing.distrorelease = %s AND
            SourcePackagePublishing.status = %s AND
            SourcePackagePublishing.pocket = %s AND
            SourcePackagePublishing.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(
                self.id,
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingPocket.RELEASE)
        self.sourcecount = SourcePackageName.select(query,
            distinct=True,
            clauseTables=['SourcePackageRelease',
                'SourcePackagePublishing']).count()

        # next update the binary count
        clauseTables = ['DistroArchRelease', 'BinaryPackagePublishing',
                        'BinaryPackageRelease']
        query = """
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishing.status = %s AND
            BinaryPackagePublishing.pocket = %s AND
            BinaryPackagePublishing.distroarchrelease =
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
        result = POTemplate.selectBy(distroreleaseID=self.id)
        result = result.prejoin(['potemplatename'])
        return sorted(result,
            key=lambda x: (-x.priority, x.potemplatename.name))

    # XXX: this is expensive and shouldn't be a property
    #   -- kiko, 2006-06-14
    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(distroreleaseID=self.id, iscurrent=True)
        result = result.prejoin(['potemplatename'])
        return sorted(result,
            key=lambda x: (-x.priority, x.potemplatename.name))

    @property
    def fullreleasename(self):
        return "%s %s" % (
            self.distribution.name.capitalize(), self.name.capitalize())

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistributionRelease(self)
        return BugTaskSet().search(search_params)

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
            order = ['-Specification.datecreated', 'Specification.id']

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

    def acceptSpecificationGoal(self, spec):
        """See ISpecificationGoal."""
        spec.distrorelease = self
        spec.goalstatus = SpecificationGoalStatus.ACCEPTED

    def declineSpecificationGoal(self, spec):
        """See ISpecificationGoal."""
        spec.distrorelease = self
        spec.goalstatus = SpecificationGoalStatus.DECLINED

    def acceptSpecificationGoals(self, speclist):
        """See ISpecificationGoal."""
        for spec in speclist:
            self.acceptSpecificationGoal(spec)

        # we need to flush all the changes we have made to disk, then try
        # the query again to see if we have any specs remaining in this
        # queue
        flush_database_updates()

        return self.specifications(
                        filter=[SpecificationFilter.PROPOSED]).count()

    def declineSpecificationGoals(self, speclist):
        """See ISpecificationGoal."""
        for spec in speclist:
            self.declineSpecificationGoal(spec)

        # we need to flush all the changes we have made to disk, then try
        # the query again to see if we have any specs remaining in this
        # queue
        flush_database_updates()

        return self.specifications(
                        filter=[SpecificationFilter.PROPOSED]).count()

    @cachedproperty
    def open_cve_bugtasks(self):
        """See IDistribution."""
        return list(CveSet().getOpenBugTasks(distrorelease=self))

    @cachedproperty
    def resolved_cve_bugtasks(self):
        """See IDistribution."""
        return list(CveSet().getResolvedBugTasks(distrorelease=self))

    def getDistroReleaseLanguage(self, language):
        """See IDistroRelease."""
        return DistroReleaseLanguage.selectOneBy(
            distroreleaseID=self.id,
            languageID=language.id)

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
                POTemplate.distrorelease = %s
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
        for potemplate in self.potemplates:
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
            distroreleaseID=self.id, architecturetag=archtag)
        if item is None:
            raise NotFoundError('Unknown architecture %s for %s %s' % (
                archtag, self.distribution.name, self.name))
        return item

    def getTranslatableSourcePackages(self):
        """See IDistroRelease."""
        query = """
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id)
        result = SourcePackageName.select(query, clauseTables=['POTemplate'],
            orderBy=['name'])
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

    def getPublishedReleases(self, sourcepackage_or_name, pocket=None,
                             include_pending=False, exclude_pocket=None):
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
        distrorelease =%s
        """ % sqlvalues(spn.id, self.id)]

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        published = SourcePackagePublishing.select(
            " AND ".join(queries),
            clauseTables = ['SourcePackageRelease'])

        return shortlist(published)

    def getAllReleasesByStatus(self, status):
        """See IDistroRelease."""
        queries = ['distrorelease=%s AND status=%s'
                   % sqlvalues(self.id, status)]

        unstable_states = [
            DistributionReleaseStatus.FROZEN,
            DistributionReleaseStatus.DEVELOPMENT,
            DistributionReleaseStatus.EXPERIMENTAL,
            ]

        if self.releasestatus not in unstable_states:
            # do not consider publication to RELEASE pocket in
            # CURRENT/SUPPORTED distrorelease. They must not change.
            queries.append(
                'pocket!=%s' % sqlvalues(PackagePublishingPocket.RELEASE))

        return SourcePackagePublishing.select(" AND ".join(queries))

    def getBinaryPackagePublishing(self, name=None, version=None, archtag=None,
                                   sourcename=None, orderBy=None):
        """See IDistroRelease."""

        clauseTables = ['BinaryPackagePublishing', 'DistroArchRelease',
                        'BinaryPackageRelease', 'BinaryPackageName', 'Build',
                        'SourcePackageRelease', 'SourcePackageName' ]

        query = ['''BinaryPackagePublishing.binarypackagerelease =
                        BinaryPackageRelease.id AND
                    BinaryPackagePublishing.distroarchrelease =
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
                    BinaryPackagePublishing.status = %s'''
            % sqlvalues(self.id, PackagePublishingStatus.PUBLISHED)]

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

        query = " AND ".join(query)

        result = BinaryPackagePublishing.select(query, distinct=False,
                                                clauseTables=clauseTables,
                                                orderBy=orderBy)

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

    def createUploadedSourcePackageRelease(self, sourcepackagename,
            version, maintainer, dateuploaded, builddepends,
            builddependsindep, architecturehintlist, component,
            creator, urgency, changelog, dsc, dscsigningkey, section,
            manifest):
        """See IDistroRelease."""
        return SourcePackageRelease(uploaddistrorelease=self.id,
                                    sourcepackagename=sourcepackagename,
                                    version=version,
                                    maintainer=maintainer,
                                    dateuploaded=dateuploaded,
                                    builddepends=builddepends,
                                    builddependsindep=builddependsindep,
                                    architecturehintlist=architecturehintlist,
                                    component=component,
                                    creator=creator,
                                    urgency=urgency,
                                    changelog=changelog,
                                    dsc=dsc,
                                    dscsigningkey=dscsigningkey,
                                    section=section,
                                    manifest=manifest)

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

    def removeOldCacheItems(self):
        """See IDistroRelease."""

        # get the set of package names that should be there
        bpns = set(BinaryPackageName.select("""
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease',
                'BinaryPackageRelease']))

        # remove the cache entries for binary packages we no longer want
        for cache in self.binary_package_caches:
            if cache.binarypackagename not in bpns:
                cache.destroySelf()

    def updateCompletePackageCache(self, ztm=None):
        """See IDistroRelease."""

        # get the set of package names to deal with
        bpns = list(BinaryPackageName.select("""
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
            """ % sqlvalues(self.id),
            distinct=True,
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease',
                'BinaryPackageRelease']))

        # now ask each of them to update themselves. commit every 100
        # packages
        counter = 0
        for bpn in bpns:
            self.updatePackageCache(bpn)
            counter += 1
            if counter > 99:
                counter = 0
                if ztm is not None:
                    ztm.commit()


    def updatePackageCache(self, binarypackagename):
        """See IDistroRelease."""

        # get the set of published binarypackagereleases
        bprs = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishing.binarypackagerelease AND
            BinaryPackagePublishing.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s
            """ % sqlvalues(binarypackagename.id, self.id),
            orderBy='-datecreated',
            clauseTables=['BinaryPackagePublishing', 'DistroArchRelease'],
            distinct=True)
        if bprs.count() == 0:
            return

        # find or create the cache entry
        cache = DistroReleasePackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.id, binarypackagename.id))
        if cache is None:
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
            distributionID=self.distribution.id, distroreleaseID=self.id)

    def createQueueEntry(self, pocket, changesfilename, changesfilecontent):
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
        return DistroReleaseQueue(distrorelease=self.id,
                                  status=DistroReleaseQueueStatus.NEW,
                                  pocket=pocket,
                                  changesfile=changes_file.id)

    def getQueueItems(self, status=None, name=None, version=None,
                      exact_match=False, pocket=None):
        """See IDistroRelease."""

        default_clauses = ["""
            distroreleasequeue.distrorelease = %s""" % sqlvalues(self.id)]

        # restrict result to a given pocket
        if pocket is not None:
            default_clauses.append(
                    "distroreleasequeue.pocket = %s" % sqlvalues(pocket))


        # XXX cprov 20060606: We may reorganise this code, creating
        # some new methods provided by IDistroReleaseQueueSet, as:
        # getByStatus and getByName.
        if not status:
            assert not version and not exact_match
            return DistroReleaseQueue.select(
                " AND ".join(default_clauses),
                orderBy=['-id'])

        default_clauses.append("""
        distroreleasequeue.status = %s""" % sqlvalues(status))

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

    def createBug(self, owner, title, comment, security_related=False,
                  private=False):
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

    def initialiseFromParent(self):
        """See IDistroRelease."""
        assert self.parentrelease is not None, "Parent release must be present"
        assert SourcePackagePublishingHistory.selectBy(
            distroreleaseID=self.id).count() == 0, \
            "Source Publishing must be empty"
        for arch in self.architectures:
            assert BinaryPackagePublishingHistory.selectBy(
                distroarchreleaseID=arch.id).count() == 0, \
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
        self._copy_active_translations(cur)

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
            SELECT bpp.binarypackagerelease, %s as distroarchrelease,
                   bpp.status, bpp.component, bpp.section, bpp.priority,
                   %s as datecreated, %s as datepublished, %s as pocket,
                   false as embargo
            FROM BinaryPackagePublishing AS bpp
            WHERE bpp.distroarchrelease = %s AND bpp.status in (%s, %s) AND
                  bpp.pocket = %s
            ''' % sqlvalues(arch.id, UTC_NOW, UTC_NOW,
                            PackagePublishingPocket.RELEASE.value,
                            parent_arch.id,
                            PackagePublishingStatus.PENDING.value,
                            PackagePublishingStatus.PUBLISHED.value,
                            PackagePublishingPocket.RELEASE.value))

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
            SELECT spp.sourcepackagerelease, %s as distrorelease,
                   spp.status, spp.component, spp.section, %s as datecreated,
                   %s as datepublished, %s as pocket, false as embargo
            FROM SourcePackagePublishing AS spp
            WHERE spp.distrorelease = %s AND spp.status in (%s, %s) AND
                  spp.pocket = %s
            ''' % sqlvalues(self.id, UTC_NOW, UTC_NOW,
                            PackagePublishingPocket.RELEASE.value,
                            self.parentrelease.id,
                            PackagePublishingStatus.PENDING.value,
                            PackagePublishingStatus.PUBLISHED.value,
                            PackagePublishingPocket.RELEASE.value))

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

    def _copy_active_translations(self, cur):
        """Copy active translations from the parent into this one."""
        # Create all potemplates.
        cur.execute('''
            INSERT INTO POTemplate (
                description, path, iscurrent, messagecount, owner,
                sourcepackagename, distrorelease, header, potemplatename,
                binarypackagename, languagepack, from_sourcepackagename,
                date_last_updated)
            SELECT
                pt.description AS description,
                pt.path AS path,
                pt.iscurrent AS iscurrent,
                pt.messagecount AS messagecount,
                pt.owner AS owner,
                pt.sourcepackagename AS sourcepackagename,
                %s AS distrorelease,
                pt.header AS header,
                pt.potemplatename AS potemplatename,
                pt.binarypackagename AS binarypackagename,
                pt.languagepack AS languagepack,
                pt.from_sourcepackagename AS from_sourcepackagename,
                pt.date_last_updated AS date_last_updated
            FROM
                POTemplate AS pt
            WHERE
                pt.distrorelease = %s''' % sqlvalues(
                self, self.parentrelease))

        # Create all potmsgset for the new created potemplates.
        cur.execute('''
            INSERT INTO POTMsgSet (
                primemsgid, sequence, potemplate, commenttext, filereferences,
                sourcecomment, flagscomment)
            SELECT
                ptms.primemsgid AS primemsgid,
                ptms.sequence AS sequence,
                pt2.id AS potemplate,
                ptms.commenttext AS commenttext,
                ptms.filereferences AS filereferences,
                ptms.sourcecomment AS sourcecomment,
                ptms.flagscomment AS flagscomment
            FROM
                POTMsgSet AS ptms,
                POTemplate AS pt1,
                POTemplate AS pt2
            WHERE
                ptms.potemplate = pt1.id AND
                pt1.potemplatename = pt2.potemplatename AND
                pt1.distrorelease = %s AND
                pt2.distrorelease = %s AND
                ptms.sequence > 0''' % sqlvalues(
                self.parentrelease, self))

        cur.execute('''
            INSERT INTO POMsgIDSighting (
                potmsgset, pomsgid, datefirstseen, datelastseen,
                inlastrevision, pluralform)
            SELECT
                ptms2.id AS potmsgset,
                pmis.pomsgid AS pomsgid,
                pmis.datefirstseen AS datefirstseen,
                pmis.datelastseen AS datelastseen,
                pmis.inlastrevision AS inlastrevision,
                pmis.pluralform AS pluralform
            FROM
                POMsgIDSighting AS pmis,
                POTMsgSet AS ptms1,
                POTMsgSet AS ptms2,
                POTemplate AS pt1,
                POTemplate AS pt2
            WHERE
                pmis.potmsgset = ptms1.id AND
                ptms1.potemplate = pt1.id AND
                pt1.potemplatename = pt2.potemplatename AND
                pt1.distrorelease = %s AND
                pt2.distrorelease = %s AND
                ptms2.potemplate = pt2.id AND
                ptms1.primemsgid = ptms2.primemsgid''' % sqlvalues(
                self.parentrelease, self))

        cur.execute('''
            INSERT INTO POFile (
                potemplate, language, description, topcomment, header,
                fuzzyheader, lasttranslator, currentcount, updatescount,
                rosettacount, lastparsed, owner, pluralforms, variant, path,
                exportfile, exporttime, datecreated, latestsubmission,
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
                pf1.pluralforms AS pluralforms,
                pf1.variant AS variant,
                pf1.path AS path,
                pf1.exportfile AS exportfile,
                pf1.exporttime AS exporttime,
                pf1.datecreated AS datecreated,
                pf1.latestsubmission AS latestsubmission,
                pf1.from_sourcepackagename AS from_sourcepackagename
            FROM
                POFile AS pf1,
                POTemplate AS pt1,
                POTemplate AS pt2
            WHERE
                pf1.potemplate = pt1.id AND
                pt1.potemplatename = pt2.potemplatename AND
                pt1.distrorelease = %s AND
                pt2.distrorelease = %s''' % sqlvalues(
                    self.parentrelease, self))

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
                POMsgSet AS pms1,
                POFile AS pf1,
                POFile AS pf2,
                POTemplate AS pt1,
                POTemplate AS pt2,
                POTMsgSet AS ptms1,
                POTMsgSet AS ptms2
            WHERE
                pt1.potemplatename = pt2.potemplatename AND
                pt1.distrorelease = %s AND
                pt2.distrorelease = %s AND
                ptms1.potemplate = pt1.id AND
                ptms2.potemplate = pt2.id AND
                pms1.potmsgset = ptms1.id AND
                ptms1.primemsgid = ptms2.primemsgid AND
                pf1.potemplate = pt1.id AND
                pf2.potemplate = pt2.id AND
                pms1.pofile = pf1.id AND
                pf1.language = pf2.language AND
                (pf1.variant = pf2.variant OR
                 (pf1.variant IS NULL AND pf2.variant IS NULL))
                ''' % sqlvalues(self.parentrelease, self.id))

        cur.execute('''
            INSERT INTO POSubmission (
                pomsgset, pluralform, potranslation, origin, datecreated,
                person, validationstatus)
            SELECT
                pms2.id AS pomsgset,
                ps1.pluralform AS pluralform,
                ps1.potranslation AS potranslation,
                ps1.origin AS origin,
                ps1.datecreated AS datecreated,
                ps1.person AS person,
                ps1.validationstatus AS validationstatus
            FROM
                POFile AS pf1,
                POFile AS pf2,
                POMsgSet AS pms1,
                POMsgSet AS pms2,
                POTemplate AS pt1,
                POTemplate AS pt2,
                POTMsgSet AS ptms1,
                POTMsgSet AS ptms2,
                POSubmission AS ps1,
                POSelection AS psel1
            WHERE
                pt1.potemplatename = pt2.potemplatename AND
                pt1.distrorelease = %s AND
                pt2.distrorelease = %s AND
                ptms1.potemplate = pt1.id AND
                ptms2.potemplate = pt2.id AND
                pms1.potmsgset = ptms1.id AND
                pms2.potmsgset = ptms2.id AND
                pms1.pofile = pf1.id AND
                pms2.pofile = pf2.id AND
                pf1.language = pf2.language AND
                (pf1.variant = pf2.variant OR
                 (pf1.variant IS NULL AND pf2.variant IS NULL)) AND
                ptms1.primemsgid = ptms2.primemsgid AND
                ps1.pomsgset = pms1.id AND
                psel1.pomsgset = ps1.pomsgset AND
                psel1.pluralform = ps1.pluralform AND
                (psel1.activesubmission = ps1.id OR
                 psel1.publishedsubmission = ps1.id)
                ''' % sqlvalues(self.parentrelease, self))

        cur.execute('''
            INSERT INTO POSelection (
                pomsgset, pluralform, activesubmission, publishedsubmission)
            SELECT
                pms2.id AS pomsgset,
                psel1.pluralform AS pluralform,
                ps3.id AS activesubmission,
                ps4.id AS publishedsubmission
            FROM
                POTemplate AS pt1
                JOIN POTMsgSet AS ptms1 ON
                    ptms1.potemplate = pt1.id AND
                    ptms1.sequence > 0
                JOIN POFile AS pf1 ON
                    pf1.potemplate = pt1.id
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POSelection AS psel1 ON
                    psel1.pomsgset = pms1.id
                LEFT OUTER JOIN POSubmission AS ps1 ON
                    ps1.id = psel1.activesubmission AND
                    ps1.pluralform = psel1.pluralform
                LEFT OUTER JOIN POSubmission AS ps2 ON
                    ps2.id = psel1.publishedsubmission AND
                    ps2.pluralform = psel1.pluralform
                JOIN POTemplate AS pt2 ON
                    pt1.potemplatename = pt2.potemplatename AND
                    pt2.distrorelease = %s
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.sequence = pms1.sequence AND
                    pms2.pofile = pf2.id
                LEFT OUTER JOIN POSubmission AS ps3 ON
                    ps3.pomsgset = pms2.id AND
                    ps3.potranslation = ps1.potranslation AND
                    ps3.pluralform = ps1.pluralform
                LEFT OUTER JOIN POSubmission AS ps4 ON
                    ps4.pomsgset = pms2.id AND
                    ps4.potranslation = ps2.potranslation AND
                    ps4.pluralform = ps2.pluralform
            WHERE
                pt1.distrorelease = %s''' % sqlvalues(
                self, self.parentrelease))

    def copyMissingTranslationsFromParent(self, ztm=None):
        """See IDistroRelease."""
        assert len(self.potemplates) > 0, (
            "%s doesn't have any translation." % self.displayname)

        if self.parent is None:
            # We don't have a parent from where we could copy translations.
            return

        cur = cursor()
        cur.execute('''
            SELECT id, potemplatename
            FROM POTemplate
            WHERE distrorelease = %s''' % sqlvalues(self.parent))
        parent_distrorelease_rows = cur.fetchall()
        parent_potemplatenames = {}
        for row in parent_distrorelease_rows:
            parent_potemplatenames[row[1]] = row[0]

        cur = cursor()
        cur.execute('''
            SELECT id, potemplatename
            FROM POTemplate
            WHERE distrorelease = %s''' % sqlvalues(self))
        current_distrorelease_rows = cur.fetchall()
        # We get the list of potemplates that we should check to get
        # translations from. If current distro release lacks that
        # potemplatename, we are not interested on it.
        potemplate_ids = [
            entry[0] for entry in rows
            if entry[1] in parent_potemplatenames
            ]
        cur.execute('''
            INSERT INTO POFile (
                potemplate, language, description, topcomment, header,
                fuzzyheader, lasttranslator, currentcount, updatescount,
                rosettacount, lastparsed, owner, pluralforms, variant, path,
                exportfile, exporttime, datecreated, latestsubmission,
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
                pf1.pluralforms AS pluralforms,
                pf1.variant AS variant,
                pf1.path AS path,
                pf1.exportfile AS exportfile,
                pf1.exporttime AS exporttime,
                pf1.datecreated AS datecreated,
                pf1.latestsubmission AS latestsubmission,
                pf1.from_sourcepackagename AS from_sourcepackagename
            FROM
                POTemplate AS pt1
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.distrorelease = %s
                LEFT OUTER JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
            WHERE
                pt1.distrorelease = %s AND pf2.id IS NULL''' % sqlvalues(
            self, self.parentrelease))

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
                POTemplate AS pt1,
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.distrorelease = %s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                LEFT OUTER JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.pofile = pf2.id
            WHERE
                pt1.distrorelease = %s AND
                pms2.id IS NULL
                ''' % sqlvalues(self, self.parentrelease))

        cur.execute('''
            INSERT INTO POSubmission (
                pomsgset, pluralform, potranslation, origin, datecreated,
                person, validationstatus)
            SELECT
                pms2.id AS pomsgset,
                ps1.pluralform AS pluralform,
                ps1.potranslation AS potranslation,
                ps1.origin AS origin,
                ps1.datecreated AS datecreated,
                ps1.person AS person,
                ps1.validationstatus AS validationstatus
            FROM
                POTemplate AS pt1,
                JOIN POFile AS pf1 ON pf1.potemplate = pt1.id
                JOIN POTemplate AS pt2 ON
                    pt2.potemplatename = pt1.potemplatename AND
                    pt2.distrorelease = %s
                JOIN POFile AS pf2 ON
                    pf2.potemplate = pt2.id AND
                    pf2.language = pf1.language AND
                    (pf2.variant = pf1.variant OR
                     (pf2.variant IS NULL AND pf1.variant IS NULL))
                JOIN POMsgSet AS pms1 ON
                    pms1.potmsgset = ptms1.id AND
                    pms1.pofile = pf1.id
                JOIN POTMsgSet AS ptms1 ON ptms1.potemplate = pt1.id
                JOIN POTMsgSet AS ptms2 ON
                    ptms2.potemplate = pt2.id AND
                    ptms2.primemsgid = ptms1.primemsgid
                JOIN POMsgSet AS pms2 ON
                    pms2.potmsgset = ptms2.id AND
                    pms2.pofile = pf2.id
                JOIN POSubmission AS ps1 ON
                    ps1.pomsgset = pms1.id
                JOIN POSelection AS psel1 ON
                    psel1.pomsgset = ps1.pomsgset AND
                    psel1.pluralform = ps1.pluralform AND
                    (psel1.activesubmission = ps1.id OR
                     psel1.publishedsubmission = ps1.id)
                LEFT OUTER JOIN POSelection AS psel2 ON
                    psel1.
            WHERE
                pt1.distrorelease = %s
                ''' % sqlvalues(self.parentrelease, self))

        # Create/update POSelection.

#            potemplate = POTemplate.get(potemplate_id)
#            potemplate.copyMissingTranslations(
#                parent_potemplates[potemplate.potemplatename.id])
#            if ztm is not None:
#                ztm.commit()


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
        return DistroRelease.selectOneBy(
            distributionID=distribution.id, name=name)

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
                # XXX cprov 20060606: FROZEN is considered closed now
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

