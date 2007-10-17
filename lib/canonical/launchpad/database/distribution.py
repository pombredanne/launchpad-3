# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Database classes for implementing distribution items."""

__metaclass__ = type
__all__ = ['Distribution', 'DistributionSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    BoolCol, ForeignKey, SQLMultipleJoin, SQLRelatedJoin, StringCol,
    SQLObjectNotFound)
from sqlobject.sqlbuilder import AND, OR, SQLConstant

from canonical.cachedproperty import cachedproperty

from canonical.database.sqlbase import quote, quote_like, SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.constants import UTC_NOW

from canonical.launchpad.database.bugtarget import BugTargetBase

from canonical.launchpad.database.karma import KarmaContextMixin
from canonical.launchpad.database.archive import Archive
from canonical.launchpad.database.bug import (
    BugSet, get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.faq import FAQ, FAQSearch
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.question import (
    QuestionTargetSearch, QuestionTargetMixin)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.sprint import HasSprintsMixin
from canonical.launchpad.database.distroseries import DistroSeries
from canonical.launchpad.database.publishedpackage import PublishedPackage
from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.distributionbounty import DistributionBounty
from canonical.launchpad.database.distributionmirror import DistributionMirror
from canonical.launchpad.database.distributionsourcepackage import (
    DistributionSourcePackage)
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.distributionsourcepackagecache import (
    DistributionSourcePackageCache)
from canonical.launchpad.database.sourcepackagename import (
    SourcePackageName)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing,
    SourcePackagePublishingHistory)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp.url import urlparse

from canonical.lp.dbschema import (
    ArchivePurpose, DistroSeriesStatus, PackagePublishingStatus,
    PackageUploadStatus, SpecificationDefinitionStatus, SpecificationFilter,
    SpecificationImplementationStatus, SpecificationSort)

from canonical.launchpad.interfaces import (
    BugTaskStatus, IArchiveSet, IBuildSet, IDistribution, IDistributionSet,
    IFAQTarget, IHasBuildRecords, IHasIcon, IHasLogo, IHasMugshot,
    ILaunchpadCelebrities, IQuestionTarget, ISourcePackageName, MirrorContent,
    NotFoundError, QUESTION_STATUS_DEFAULT_SEARCH, TranslationPermission)

from canonical.archivepublisher.debversion import Version

from canonical.launchpad.validators.name import sanitize_name, valid_name


class Distribution(SQLBase, BugTargetBase, HasSpecificationsMixin,
                   HasSprintsMixin, HasTranslationImportsMixin,
                   KarmaContextMixin, QuestionTargetMixin):
    """A distribution of an operating system, e.g. Debian GNU/Linux."""
    implements(
        IDistribution, IFAQTarget, IHasBuildRecords, IQuestionTarget,
        IHasLogo, IHasMugshot, IHasIcon)

    _table = 'Distribution'
    _defaultOrder = 'name'

    name = StringCol(notNull=True, alternateID=True, unique=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
    domainname = StringCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    bugcontact = ForeignKey(
        dbName='bugcontact', foreignKey='Person', notNull=False, default=None)
    security_contact = ForeignKey(
        dbName='security_contact', foreignKey='Person', notNull=False,
        default=None)
    driver = ForeignKey(
        foreignKey="Person", dbName="driver", notNull=False, default=None)
    members = ForeignKey(dbName='members', foreignKey='Person', notNull=True)
    mirror_admin = ForeignKey(
        dbName='mirror_admin', foreignKey='Person', notNull=True)
    translationgroup = ForeignKey(
        dbName='translationgroup', foreignKey='TranslationGroup',
        notNull=False, default=None)
    translationpermission = EnumCol(
        dbName='translationpermission', notNull=True,
        schema=TranslationPermission, default=TranslationPermission.OPEN)
    lucilleconfig = StringCol(
        dbName='lucilleconfig', notNull=False, default=None)
    upload_sender = StringCol(
        dbName='upload_sender', notNull=False, default=None)
    upload_admin = ForeignKey(
        dbName='upload_admin', foreignKey='Person', default=None,
        notNull=False)
    bounties = SQLRelatedJoin(
        'Bounty', joinColumn='distribution', otherColumn='bounty',
        intermediateTable='DistributionBounty')
    uploaders = SQLMultipleJoin('DistroComponentUploader',
        joinColumn='distribution', prejoins=["uploader", "component"])
    official_answers = BoolCol(dbName='official_answers', notNull=True,
        default=False)
    official_malone = BoolCol(dbName='official_malone', notNull=True,
        default=False)
    official_rosetta = BoolCol(dbName='official_rosetta', notNull=True,
        default=False)
    translation_focus = ForeignKey(dbName='translation_focus',
        foreignKey='DistroSeries', notNull=False, default=None)
    source_package_caches = SQLMultipleJoin('DistributionSourcePackageCache',
                                            joinColumn="distribution",
                                            orderBy="name",
                                            prejoins=['sourcepackagename'])
    date_created = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    language_pack_admin = ForeignKey(dbName='language_pack_admin',
        foreignKey='Person', notNull=False, default=None)

    @cachedproperty
    def main_archive(self):
        """See `IDistribution`."""
        return Archive.selectOneBy(distribution=self,
                                   purpose=ArchivePurpose.PRIMARY)

    @cachedproperty
    def all_distro_archives(self):
        """See `IDistribution`."""
        return Archive.select("""
            Distribution = %s AND
            Purpose != %s""" % sqlvalues(self.id, ArchivePurpose.PPA)
            )

    @cachedproperty
    def all_distro_archive_ids(self):
        """See `IDistribution`."""
        return [archive.id for archive in self.all_distro_archives]

    def archiveIdList(self, archive=None):
        """See `IDistribution`."""
        if archive is None:
            return self.all_distro_archive_ids
        else:
            return [archive.id]

    @property
    def all_milestones(self):
        """See `IDistribution`."""
        return Milestone.selectBy(
            distribution=self, orderBy=['dateexpected', 'name'])

    @property
    def milestones(self):
        """See `IDistribution`."""
        return Milestone.selectBy(
            distribution=self, visible=True, orderBy=['dateexpected', 'name'])

    @property
    def archive_mirrors(self):
        """See canonical.launchpad.interfaces.IDistribution."""
        return DistributionMirror.selectBy(
            distribution=self, content=MirrorContent.ARCHIVE,
            official_approved=True, official_candidate=True, enabled=True)

    @property
    def cdimage_mirrors(self):
        """See canonical.launchpad.interfaces.IDistribution."""
        return DistributionMirror.selectBy(
            distribution=self, content=MirrorContent.RELEASE,
            official_approved=True, official_candidate=True, enabled=True)

    @property
    def disabled_mirrors(self):
        """See canonical.launchpad.interfaces.IDistribution."""
        return DistributionMirror.selectBy(
            distribution=self, official_approved=True,
            official_candidate=True, enabled=False)

    @property
    def unofficial_mirrors(self):
        """See canonical.launchpad.interfaces.IDistribution."""
        query = OR(DistributionMirror.q.official_candidate==False,
                   DistributionMirror.q.official_approved==False)
        return DistributionMirror.select(
            AND(DistributionMirror.q.distributionID==self.id, query))

    @property
    def full_functionality(self):
        """See `IDistribution`."""
        if self == getUtility(ILaunchpadCelebrities).ubuntu:
            return True
        return False

    @property
    def drivers(self):
        """See `IDistribution`."""
        if self.driver is not None:
            return [self.driver]
        else:
            return [self.owner]

    @property
    def is_read_only(self):
        """See `IDistribution`."""
        return self.name in ['debian', 'redhat', 'gentoo']

    @property
    def _sort_key(self):
        """Return something that can be used to sort distributions,
        putting Ubuntu and its major derivatives first.

        This is used to ensure that the list of distributions displayed in
        Soyuz generally puts Ubuntu at the top.
        """
        if self.name == 'ubuntu':
            return (0, 'ubuntu')
        if self.name in ['kubuntu', 'xubuntu', 'edubuntu']:
            return (1, self.name)
        if 'buntu' in self.name:
            return (2, self.name)
        return (3, self.name)

    @property
    def serieses(self):
        """See `IDistribution`."""
        # This is used in a number of places and given it's already
        # listified, why not spare the trouble of regenerating?
        ret = DistroSeries.selectBy(distribution=self)
        return sorted(ret, key=lambda a: Version(a.version), reverse=True)

    @property
    def mentoring_offers(self):
        """See `IDistribution`"""
        via_specs = MentoringOffer.select("""
            Specification.distribution = %s AND
            Specification.id = MentoringOffer.specification
            """ % sqlvalues(self.id) + """ AND NOT (
            """ + Specification.completeness_clause + ")",
            clauseTables=['Specification'],
            distinct=True)
        via_bugs = MentoringOffer.select("""
            BugTask.distribution = %s AND
            BugTask.bug = MentoringOffer.bug AND
            BugTask.bug = Bug.id AND
            Bug.private IS FALSE
            """ % sqlvalues(self.id) + """ AND NOT (
            """ + BugTask.completeness_clause +")",
            clauseTables=['BugTask', 'Bug'],
            distinct=True)
        return via_specs.union(via_bugs, orderBy=['-date_created', '-id'])

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.displayname

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return self.name

    def _getBugTaskContextWhereClause(self):
        """See BugTargetBase."""
        return "BugTask.distribution = %d" % self.id

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistribution(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        return get_bug_tags("BugTask.distribution = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See `IBugTarget`."""
        return get_bug_tags_open_count(
            "BugTask.distribution = %s" % sqlvalues(self), user)

    def getMirrorByName(self, name):
        """See `IDistribution`."""
        return DistributionMirror.selectOneBy(distribution=self, name=name)

    def newMirror(self, owner, speed, country, content, displayname=None,
                  description=None, http_base_url=None, ftp_base_url=None,
                  rsync_base_url=None, official_candidate=False,
                  enabled=False):
        """See `IDistribution`."""
        # NB this functionality is only available to distributions that have
        # the full functionality of Launchpad enabled. This is Ubuntu and
        # commercial derivatives that have been specifically given this
        # ability
        if not self.full_functionality:
            return None

        url = http_base_url or ftp_base_url
        assert url is not None, (
            "A mirror must provide either an HTTP or FTP URL (or both).")
        dummy, host, dummy, dummy, dummy, dummy = urlparse(url)
        name = sanitize_name('%s-%s' % (host, content.name.lower()))

        orig_name = name
        count = 1
        while DistributionMirror.selectOneBy(name=name) is not None:
            count += 1
            name = '%s%s' % (orig_name, count)

        return DistributionMirror(
            distribution=self, owner=owner, name=name, speed=speed,
            country=country, content=content, displayname=displayname,
            description=description, http_base_url=http_base_url,
            ftp_base_url=ftp_base_url, rsync_base_url=rsync_base_url,
            official_candidate=official_candidate, enabled=enabled)

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        bug_params.setBugTarget(distribution=self)
        return BugSet().createBug(bug_params)

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.distribution = %s' % sqlvalues(self)

    @property
    def currentseries(self):
        """See `IDistribution`."""
        # XXX kiko 2006-03-18:
        # This should be just a selectFirst with a case in its
        # order by clause.

        serieses = self.serieses
        # If we have a frozen one, return that.
        for series in serieses:
            if series.status == DistroSeriesStatus.FROZEN:
                return series
        # If we have one in development, return that.
        for series in serieses:
            if series.status == DistroSeriesStatus.DEVELOPMENT:
                return series
        # If we have a stable one, return that.
        for series in serieses:
            if series.status == DistroSeriesStatus.CURRENT:
                return series
        # If we have ANY, return the first one.
        if len(serieses) > 0:
            return serieses[0]
        return None

    def __getitem__(self, name):
        for series in self.serieses:
            if series.name == name:
                return series
        raise NotFoundError(name)

    def __iter__(self):
        return iter(self.serieses)

    @property
    def bugCounter(self):
        """See `IDistribution`."""
        counts = []

        severities = [BugTaskStatus.NEW,
                      BugTaskStatus.CONFIRMED,
                      BugTaskStatus.INVALID,
                      BugTaskStatus.FIXRELEASED]

        querystr = ("BugTask.distribution = %s AND "
                 "BugTask.status = %s")

        for severity in severities:
            query = querystr % sqlvalues(self.id, severity.value)
            count = BugTask.select(query).count()
            counts.append(count)

        return counts

    def getSeries(self, name_or_version):
        """See `IDistribution`."""
        distroseries = DistroSeries.selectOneBy(
            distribution=self, name=name_or_version)
        if distroseries is None:
            distroseries = DistroSeries.selectOneBy(
                distribution=self, version=name_or_version)
            if distroseries is None:
                raise NotFoundError(name_or_version)
        return distroseries

    def getDevelopmentSerieses(self):
        """See `IDistribution`."""
        return DistroSeries.selectBy(
            distribution=self,
            status=DistroSeriesStatus.DEVELOPMENT)

    def getMilestone(self, name):
        """See `IDistribution`."""
        return Milestone.selectOne("""
            distribution = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def getSourcePackage(self, name):
        """See `IDistribution`."""
        if ISourcePackageName.providedBy(name):
            sourcepackagename = name
        else:
            try:
                sourcepackagename = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistributionSourcePackage(self, sourcepackagename)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See `IDistribution`."""
        return DistributionSourcePackageRelease(self, sourcepackagerelease)

    @property
    def has_any_specifications(self):
        """See `IHasSpecifications`."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        """See `IHasSpecifications`."""
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None):
        """See `IHasSpecifications`.

        In the case of distributions, there are two kinds of filtering,
        based on:

          - completeness: we want to show INCOMPLETE if nothing is said
          - informationalness: we will show ANY if nothing is said

        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # it could be None or it could be []
            filter = [SpecificationFilter.INCOMPLETE]

        # now look at the filter and fill in the unsaid bits

        # defaults for completeness: if nothing is said about completeness
        # then we want to show INCOMPLETE
        completeness = False
        for option in [
            SpecificationFilter.COMPLETE,
            SpecificationFilter.INCOMPLETE]:
            if option in filter:
                completeness = True
        if completeness is False:
            filter.append(SpecificationFilter.INCOMPLETE)

        # defaults for acceptance: in this case we have nothing to do
        # because specs are not accepted/declined against a distro

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = (
                ['-priority', 'Specification.definition_status', 'Specification.name'])
        elif sort == SpecificationSort.DATE:
            order = ['-Specification.datecreated', 'Specification.id']

        # figure out what set of specifications we are interested in. for
        # distributions, we need to be able to filter on the basis of:
        #
        #  - completeness. by default, only incomplete specs shown
        #  - informational.
        #
        base = 'Specification.distribution = %s' % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s ' %
                quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            query += ' AND Specification.definition_status NOT IN ( %s, %s ) ' % \
                sqlvalues(SpecificationDefinitionStatus.OBSOLETE,
                          SpecificationDefinitionStatus.SUPERSEDED)

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
        """See `ISpecificationTarget`."""
        return Specification.selectOneBy(distribution=self, name=name)

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None, unsupported=False):
        """See `IQuestionCollection`."""
        if unsupported:
            unsupported_target = self
        else:
            unsupported_target = None

        return QuestionTargetSearch(
            distribution=self,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from,
            unsupported_target=unsupported_target).getResults()

    def getTargetTypes(self):
        """See `QuestionTargetMixin`.

        Defines distribution as self and sourcepackagename as None.
        """
        return {'distribution': self,
                'sourcepackagename': None}

    def questionIsForTarget(self, question):
        """See `QuestionTargetMixin`.

        Return True when the Question's distribution is self.
        """
        if question.distribution is not self:
            return False
        return True

    def newFAQ(self, owner, title, content, keywords=None, date_created=None):
        """See `IFAQTarget`."""
        return FAQ.new(
            owner=owner, title=title, content=content, keywords=keywords,
            date_created=date_created, distribution=self)

    def findSimilarFAQs(self, summary):
        """See `IFAQTarget`."""
        return FAQ.findSimilar(summary, distribution=self)

    def getFAQ(self, id):
        """See `IFAQCollection`."""
        return FAQ.getForTarget(id, self)

    def searchFAQs(self, search_text=None, owner=None, sort=None):
        """See `IFAQCollection`."""
        return FAQSearch(
            search_text=search_text, owner=owner, sort=sort,
            distribution=self).getResults()

    def ensureRelatedBounty(self, bounty):
        """See `IDistribution`."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        DistributionBounty(distribution=self, bounty=bounty)

    def getDistroSeriesAndPocket(self, distroseries_name):
        """See `IDistribution`."""
        from canonical.archivepublisher.publishing import suffixpocket

        # Get the list of suffixes.
        suffixes = [suffix for suffix, ignored in suffixpocket.items()]
        # Sort it longest string first.
        suffixes.sort(key=len, reverse=True)

        for suffix in suffixes:
            if distroseries_name.endswith(suffix):
                try:
                    left_size = len(distroseries_name) - len(suffix)
                    return (self[distroseries_name[:left_size]],
                            suffixpocket[suffix])
                except KeyError:
                    # Swallow KeyError to continue round the loop.
                    pass

        raise NotFoundError(distroseries_name)

    def getFileByName(self, filename, archive=None, source=True, binary=True):
        """See `IDistribution`."""
        assert (source or binary), "searching in an explicitly empty " \
               "space is pointless"
        if archive is None:
            archive = self.main_archive

        if source:
            candidate = SourcePackageFilePublishing.selectFirstBy(
                distribution=self, libraryfilealiasfilename=filename,
                archive=archive, orderBy=['id'])

        if binary:
            candidate = BinaryPackageFilePublishing.selectFirstBy(
                distribution=self,
                libraryfilealiasfilename=filename,
                archive=archive, orderBy=["-id"])

        if candidate is not None:
            return candidate.libraryfilealias

        raise NotFoundError(filename)

    def getBuildRecords(self, build_state=None, name=None, pocket=None):
        """See `IHasBuildRecords`"""
        # Find out the distroarchseriess in question.
        arch_ids = []
        # concatenate architectures list since they are distinct.
        for series in self.serieses:
            arch_ids += [arch.id for arch in series.architectures]

        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds(
            arch_ids, build_state, name, pocket)

    def removeOldCacheItems(self, log):
        """See `IDistribution`."""

        # Get the set of source package names to deal with.
        spns = set(SourcePackageName.select("""
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id AND
            SourcePackagePublishingHistory.dateremoved is NULL
            """ % sqlvalues(self, self.all_distro_archive_ids),
            distinct=True,
            clauseTables=['SourcePackagePublishingHistory', 'DistroRelease',
                'SourcePackageRelease']))

        # Remove the cache entries for packages we no longer publish.
        for cache in self.source_package_caches:
            if cache.sourcepackagename not in spns:
                log.debug(
                    "Removing source cache for '%s' (%s)"
                    % (cache.name, cache.id))
                cache.destroySelf()

    def updateCompleteSourcePackageCache(self, log, ztm):
        """See `IDistribution`."""
        # Get the set of source package names to deal with.
        spns = list(SourcePackageName.select("""
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id AND
            SourcePackagePublishingHistory.dateremoved is NULL
            """ % sqlvalues(self, self.all_distro_archive_ids),
            distinct=True,
            clauseTables=['SourcePackagePublishingHistory', 'DistroRelease',
                'SourcePackageRelease']))

        # Now update, committing every 50 packages.
        counter = 0
        for spn in spns:
            log.debug("Considering source '%s'" % spn.name)
            self.updateSourcePackageCache(spn, log)
            counter += 1
            if counter > 49:
                counter = 0
                log.debug("Committing")
                ztm.commit()

    def updateSourcePackageCache(self, sourcepackagename, log):
        """See `IDistribution`."""

        # Get the set of published sourcepackage releases.
        sprs = list(SourcePackageRelease.select("""
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.id =
                SourcePackagePublishingHistory.sourcepackagerelease AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.dateremoved is NULL
            """ % sqlvalues(sourcepackagename, self,
                            self.all_distro_archive_ids),
            orderBy='id',
            clauseTables=['SourcePackagePublishingHistory', 'DistroRelease'],
            distinct=True))

        if len(sprs) == 0:
            log.debug("No sources releases found.")
            return

        # Find or create the cache entry.
        cache = DistributionSourcePackageCache.selectOne("""
            distribution = %s AND
            sourcepackagename = %s
            """ % sqlvalues(self.id, sourcepackagename.id))
        if cache is None:
            log.debug("Creating new source cache entry.")
            cache = DistributionSourcePackageCache(
                distribution=self,
                sourcepackagename=sourcepackagename)

        # Make sure the name is correct.
        cache.name = sourcepackagename.name

        # Get the sets of binary package names, summaries, descriptions.

        # XXX Julian 2007-04-03:
        # This bit of code needs fixing up, it is doing stuff that
        # really needs to be done in SQL, such as sorting and uniqueness.
        # This would also improve the performance.
        binpkgnames = set()
        binpkgsummaries = set()
        binpkgdescriptions = set()
        sprchangelog = set()
        for spr in sprs:
            log.debug("Considering source version %s" % spr.version)
            # changelog may be empty, in which case we don't want to add it
            # to the set as the join would fail below.
            if spr.changelog is not None:
                sprchangelog.add(spr.changelog)
            binpkgs = BinaryPackageRelease.select("""
                BinaryPackageRelease.build = Build.id AND
                Build.sourcepackagerelease = %s
                """ % sqlvalues(spr.id),
                clauseTables=['Build'])
            for binpkg in binpkgs:
                log.debug("Considering binary '%s'" % binpkg.name)
                binpkgnames.add(binpkg.name)
                binpkgsummaries.add(binpkg.summary)
                binpkgdescriptions.add(binpkg.description)

        # Update the caches.
        cache.binpkgnames = ' '.join(sorted(binpkgnames))
        cache.binpkgsummaries = ' '.join(sorted(binpkgsummaries))
        cache.binpkgdescriptions = ' '.join(sorted(binpkgdescriptions))
        cache.changelog = ' '.join(sorted(sprchangelog))

    def searchSourcePackages(self, text):
        """See `IDistribution`."""
        # The query below tries exact matching on the source package
        # name as well; this is because source package names are
        # notoriously bad for fti matching -- they can contain dots, or
        # be short like "at", both things which users do search for.
        dspcaches = DistributionSourcePackageCache.select("""
            distribution = %s AND
            (fti @@ ftq(%s) OR
             DistributionSourcePackageCache.name ILIKE '%%' || %s || '%%')
            """ % (quote(self.id), quote(text), quote_like(text)),
            orderBy=[SQLConstant('rank(fti, ftq(%s)) DESC' % quote(text))],
            prejoins=["sourcepackagename"])
        return [dspc.distributionsourcepackage for dspc in dspcaches]

    def guessPackageNames(self, pkgname):
        """See `IDistribution`"""
        assert isinstance(pkgname, basestring), (
            "Expected string. Got: %r" % pkgname)

        pkgname = pkgname.strip().lower()
        if not valid_name(pkgname):
            raise NotFoundError('Invalid package name: %s' % pkgname)

        if self.currentseries is None:
            # Distribution with no series can't have anything
            # published in it.
            raise NotFoundError('%s has no series; %r was never '
                                'published in it'
                                % (self.displayname, pkgname))

        # The way this method works is that is tries to locate a pair
        # of packages related to that name. If it locates a source
        # package it then tries to see if it has been published at any
        # point, and gets the binary package from the publishing
        # record.
        #
        # If that fails (no source package by that name, or not
        # published) then it'll search binary packages, then find the
        # source package most recently associated with it, first in
        # the current distroseries and then across the whole
        # distribution.
        #
        # XXX kiko 2006-07-28:
        # Note that the strategy of falling back to previous
        # distribution series might be revisited in the future; for
        # instance, when people file bugs, it might actually be bad for
        # us to allow them to be associated with obsolete packages.

        sourcepackagename = SourcePackageName.selectOneBy(name=pkgname)
        if sourcepackagename:
            # Note that in the source package case, we don't restrict
            # the search to the distribution release, making a best
            # effort to find a package.
            publishing = SourcePackagePublishingHistory.selectFirst('''
                SourcePackagePublishingHistory.distrorelease =
                    DistroRelease.id AND
                DistroRelease.distribution = %s AND
                SourcePackagePublishingHistory.archive IN %s AND
                SourcePackagePublishingHistory.sourcepackagerelease =
                    SourcePackageRelease.id AND
                SourcePackageRelease.sourcepackagename = %s AND
                SourcePackagePublishingHistory.status = %s
                ''' % sqlvalues(self,
                                self.all_distro_archive_ids,
                                sourcepackagename,
                                PackagePublishingStatus.PUBLISHED),
                clauseTables=['SourcePackageRelease', 'DistroRelease'],
                distinct=True,
                orderBy="id")
            if publishing is not None:
                # Attempt to find a published binary package of the
                # same name. Try the current release first.
                publishedpackage = PublishedPackage.selectFirstBy(
                    sourcepackagename=sourcepackagename.name,
                    binarypackagename=sourcepackagename.name,
                    distroseries=self.currentseries,
                    orderBy=['-id'])
                if publishedpackage is None:
                    # Try any release next.
                    # XXX Gavin Panella 2007-04-18:
                    # Could we just do this first? I'm just
                    # following the pattern that was here before
                    # (e.g. see the search for a binary package below).
                    publishedpackage = PublishedPackage.selectFirstBy(
                        sourcepackagename=sourcepackagename.name,
                        binarypackagename=sourcepackagename.name,
                        distribution=self,
                        orderBy=['-id'])
                if publishedpackage is not None:
                    binarypackagename = BinaryPackageName.byName(
                        publishedpackage.binarypackagename)
                    return (sourcepackagename, binarypackagename)
                # No binary with a similar name, so just return None
                # rather than returning some arbitrary binary package.
                return (sourcepackagename, None)

        # At this point we don't have a published source package by
        # that name, so let's try to find a binary package and work
        # back from there.
        binarypackagename = BinaryPackageName.selectOneBy(name=pkgname)
        if binarypackagename:
            # Ok, so we have a binarypackage with that name. Grab its
            # latest publication -- first in the distribution series
            # and if that fails, in the distribution (this may be an old
            # package name the end-user is groping for) -- and then get
            # the sourcepackagename from that.
            publishing = PublishedPackage.selectFirstBy(
                binarypackagename=binarypackagename.name,
                distroseries=self.currentseries,
                orderBy=['-id'])
            if publishing is None:
                publishing = PublishedPackage.selectFirstBy(
                    binarypackagename=binarypackagename.name,
                    distribution=self,
                    orderBy=['-id'])
            if publishing is not None:
                sourcepackagename = SourcePackageName.byName(
                                        publishing.sourcepackagename)
                return (sourcepackagename, binarypackagename)

        # We got nothing so signal an error.
        if sourcepackagename is None:
            # Not a binary package name, not a source package name,
            # game over!
            if binarypackagename:
                raise NotFoundError('Binary package %s not published in %s'
                                    % (pkgname, self.displayname))
            else:
                raise NotFoundError('Unknown package: %s' % pkgname)
        else:
            raise NotFoundError('Package %s not published in %s'
                                % (pkgname, self.displayname))

    def getAllPPAs(self):
        """See `IDistribution`"""
        return Archive.selectBy(
            purpose=ArchivePurpose.PPA, distribution=self, orderBy=['id'])

    def getPPAByOwnerName(self, name):
        """See `IDistribution`"""
        query = """
            Archive.purpose = %s AND
            Archive.distribution = %s AND
            Person.id = Archive.owner AND
            Person.name = %s
        """ % sqlvalues(ArchivePurpose.PPA, self, name)
        return Archive.selectOne(query, clauseTables=['Person'])

    def searchPPAs(self, text=None, show_inactive=False):
        """See `IDistribution`."""
        clauses = ["""
        Archive.purpose = %s AND
        Archive.distribution = %s AND
        Person.id = Archive.owner
        """ % sqlvalues(ArchivePurpose.PPA, self)]

        clauseTables = ['Person']
        orderBy = ['Person.name']

        if not show_inactive:
            active_statuses = (PackagePublishingStatus.PUBLISHED,
                               PackagePublishingStatus.PENDING)
            clauses.append("""
            Archive.id IN (
                SELECT DISTINCT archive FROM SourcepackagePublishingHistory
                WHERE status IN %s)
            """ % sqlvalues(active_statuses))

        if text:
            clauses.append("""
            ((Person.fti @@ ftq(%s) OR
            Archive.description LIKE '%%' || %s || '%%'))
            """ % (quote(text), quote_like(text)))

        query = ' AND '.join(clauses)
        return Archive.select(
            query, orderBy=orderBy, clauseTables=clauseTables)

    def getPendingAcceptancePPAs(self):
        """See `IDistribution`."""
        query = """
        Archive.purpose = %s AND
        Archive.distribution = %s AND
        PackageUpload.archive = Archive.id AND
        PackageUpload.status = %s
        """ % sqlvalues(ArchivePurpose.PPA, self,
                        PackageUploadStatus.ACCEPTED)

        return Archive.select(
            query, clauseTables=['PackageUpload'],
            orderBy=['archive.id'], distinct=True)

    def getPendingPublicationPPAs(self):
        """See `IDistribution`."""
        src_query = """
        Archive.purpose = %s AND
        Archive.distribution = %s AND
        SourcePackagePublishingHistory.archive = archive.id AND
        SourcePackagePublishingHistory.status = %s
         """ % sqlvalues(ArchivePurpose.PPA, self,
                         PackagePublishingStatus.PENDING)

        src_archives = Archive.select(
            src_query, clauseTables=['SourcePackagePublishingHistory'],
            orderBy=['archive.id'], distinct=True)

        bin_query = """
        Archive.purpose = %s AND
        Archive.distribution = %s AND
        BinaryPackagePublishingHistory.archive = archive.id AND
        BinaryPackagePublishingHistory.status = %s
        """ % sqlvalues(ArchivePurpose.PPA, self,
                        PackagePublishingStatus.PENDING)

        bin_archives = Archive.select(
            bin_query, clauseTables=['BinaryPackagePublishingHistory'],
            orderBy=['archive.id'], distinct=True)

        return src_archives.union(bin_archives)

    def getArchiveByComponent(self, component_name):
        """See `IDistribution`."""
        # XXX Julian 2007-08-16
        # These component names should be Soyuz-wide constants.
        componentMapToArchivePurpose = {
            'main' : ArchivePurpose.PRIMARY,
            'restricted' : ArchivePurpose.PRIMARY,
            'universe' : ArchivePurpose.PRIMARY,
            'multiverse' : ArchivePurpose.PRIMARY,
            'partner' : ArchivePurpose.PARTNER,
            }

        try:
            # Map known components.
            return getUtility(IArchiveSet).getByDistroPurpose(self,
                componentMapToArchivePurpose[component_name])
        except KeyError:
            # Otherwise we defer to the caller.
            return None


class DistributionSet:
    """This class is to deal with Distribution related stuff"""

    implements(IDistributionSet)

    def __init__(self):
        self.title = "Registered Distributions"

    def __iter__(self):
        """Return all distributions sorted with Ubuntu preferentially
        displayed.
        """
        distroset = Distribution.select()
        return iter(sorted(shortlist(distroset,100),
                        key=lambda distro: distro._sort_key))

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        distribution = self.getByName(name)
        if distribution is None:
            raise NotFoundError(name)
        return distribution

    def get(self, distributionid):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        return Distribution.get(distributionid)

    def count(self):
        """See `IDistributionSet`."""
        return Distribution.select().count()

    def getDistros(self):
        """Returns all Distributions available on the database"""
        return Distribution.select()

    def getByName(self, distroname):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        try:
            return Distribution.byName(distroname)
        except SQLObjectNotFound:
            return None

    def new(self, name, displayname, title, description, summary, domainname,
            members, owner, mugshot=None, logo=None, icon=None):
        """See `IDistributionSet`."""
        distro = Distribution(
            name=name,
            displayname=displayname,
            title=title,
            description=description,
            summary=summary,
            domainname=domainname,
            members=members,
            mirror_admin=owner,
            owner=owner,
            mugshot=mugshot,
            logo=logo,
            icon=icon)
        archive = getUtility(IArchiveSet).new(distribution=distro,
            purpose=ArchivePurpose.PRIMARY)
        return distro
