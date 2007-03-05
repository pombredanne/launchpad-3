# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Distribution', 'DistributionSet']

from operator import attrgetter

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    BoolCol, ForeignKey, SQLMultipleJoin, SQLRelatedJoin, StringCol,
    SQLObjectNotFound)
from sqlobject.sqlbuilder import AND, OR, SQLConstant

from canonical.database.sqlbase import quote, quote_like, SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.launchpad.database.bugtarget import BugTargetBase

from canonical.launchpad.database.karma import KarmaContextMixin
from canonical.launchpad.database.answercontact import AnswerContact
from canonical.launchpad.database.bug import (
    BugSet, get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.question import (
    SimilarQuestionsSearch, Question, QuestionTargetSearch, QuestionSet)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.sprint import Sprint
from canonical.launchpad.database.distrorelease import DistroRelease
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
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.sourcepackagename import (
    SourcePackageName)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing,
    SourcePackagePublishingHistory)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp.url import urlparse

from canonical.lp.dbschema import (
    BugTaskStatus, DistributionReleaseStatus, MirrorContent,
    TranslationPermission, SpecificationSort, SpecificationFilter,
    SpecificationStatus, PackagePublishingStatus)

from canonical.launchpad.interfaces import (
    IBuildSet, IDistribution, IDistributionSet, IHasBuildRecords,
    ILaunchpadCelebrities, ISourcePackageName, IQuestionTarget, NotFoundError,
    get_supported_languages, QUESTION_STATUS_DEFAULT_SEARCH)

from sourcerer.deb.version import Version

from canonical.launchpad.validators.name import valid_name, sanitize_name


class Distribution(SQLBase, BugTargetBase, HasSpecificationsMixin,
                   KarmaContextMixin):
    """A distribution of an operating system, e.g. Debian GNU/Linux."""
    implements(IDistribution, IHasBuildRecords, IQuestionTarget)

    _defaultOrder = 'name'

    name = StringCol(notNull=True, alternateID=True, unique=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    homepage_content = StringCol(default=None)
    emblem = ForeignKey(
        dbName='emblem', foreignKey='LibraryFileAlias', default=None)
    gotchi = ForeignKey(
        dbName='gotchi', foreignKey='LibraryFileAlias', default=None)
    gotchi_heading = ForeignKey(
        dbName='gotchi_heading', foreignKey='LibraryFileAlias', default=None)
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
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=False, default=None)
    translationpermission = EnumCol(dbName='translationpermission',
        notNull=True, schema=TranslationPermission,
        default=TranslationPermission.OPEN)
    lucilleconfig = StringCol(dbName='lucilleconfig', notNull=False,
                              default=None)
    upload_sender = StringCol(dbName='upload_sender', notNull=False,
                              default=None)
    upload_admin = ForeignKey(dbName='upload_admin', foreignKey='Person',
                              default=None, notNull=False)
    bounties = SQLRelatedJoin(
        'Bounty', joinColumn='distribution', otherColumn='bounty',
        intermediateTable='DistributionBounty')
    milestones = SQLMultipleJoin('Milestone', joinColumn='distribution',
        orderBy=['dateexpected', 'name'])
    uploaders = SQLMultipleJoin('DistroComponentUploader',
        joinColumn='distribution', prejoins=["uploader", "component"])
    official_malone = BoolCol(dbName='official_malone', notNull=True,
        default=False)
    official_rosetta = BoolCol(dbName='official_rosetta', notNull=True,
        default=False)
    translation_focus = ForeignKey(dbName='translation_focus',
        foreignKey='DistroRelease', notNull=False, default=None)
    source_package_caches = SQLMultipleJoin('DistributionSourcePackageCache',
                                            joinColumn="distribution",
                                            orderBy="name",
                                            prejoins=['sourcepackagename'])
    main_archive = ForeignKey(dbName='main_archive',
        foreignKey='Archive', notNull=True)


    @property
    def archive_mirrors(self):
        """See canonical.launchpad.interfaces.IDistribution."""
        return DistributionMirror.selectBy(
            distribution=self, content=MirrorContent.ARCHIVE,
            official_approved=True, official_candidate=True, enabled=True)

    @property
    def release_mirrors(self):
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
    def coming_sprints(self):
        """See IHasSprints."""
        return Sprint.select("""
            Specification.distribution = %s AND
            Specification.id = SprintSpecification.specification AND
            SprintSpecification.sprint = Sprint.id AND
            Sprint.time_ends > 'NOW'
            """ % sqlvalues(self.id),
            clauseTables=['Specification', 'SprintSpecification'],
            orderBy='time_starts',
            distinct=True,
            limit=5)

    @property
    def full_functionality(self):
        """See IDistribution."""
        if self == getUtility(ILaunchpadCelebrities).ubuntu:
            return True
        return False

    @property
    def drivers(self):
        """See IDistribution."""
        if self.driver is not None:
            return [self.driver]
        else:
            return [self.owner]

    @property
    def is_read_only(self):
        """See IDistribution."""
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
        if self.name in ['kubuntu', 'xubuntu']:
            return (1, self.name)
        return (2, self.name)

    @property
    def releases(self):
        # This is used in a number of places and given it's already
        # listified, why not spare the trouble of regenerating?
        ret = DistroRelease.selectBy(distribution=self)
        return sorted(ret, key=lambda a: Version(a.version), reverse=True)

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return self.displayname

    def _getBugTaskContextWhereClause(self):
        """See BugTargetBase."""
        return "BugTask.distribution = %d" % self.id

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistribution(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return get_bug_tags("BugTask.distribution = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.distribution = %s" % sqlvalues(self), user)

    def getMirrorByName(self, name):
        """See IDistribution."""
        return DistributionMirror.selectOneBy(distribution=self, name=name)

    def newMirror(self, owner, speed, country, content, displayname=None,
                  description=None, http_base_url=None, ftp_base_url=None,
                  rsync_base_url=None, official_candidate=False,
                  enabled=False):
        """See IDistribution."""
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
    def currentrelease(self):
        # XXX: this should be just a selectFirst with a case in its
        # order by clause -- kiko, 2006-03-18

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

    @property
    def bugCounter(self):
        counts = []

        severities = [BugTaskStatus.UNCONFIRMED,
                      BugTaskStatus.CONFIRMED,
                      BugTaskStatus.REJECTED,
                      BugTaskStatus.FIXRELEASED]

        querystr = ("BugTask.distribution = %s AND "
                 "BugTask.status = %s")

        for severity in severities:
            query = querystr % sqlvalues(self.id, severity.value)
            count = BugTask.select(query).count()
            counts.append(count)

        return counts

    def getRelease(self, name_or_version):
        """See IDistribution."""
        distrorelease = DistroRelease.selectOneBy(
            distribution=self, name=name_or_version)
        if distrorelease is None:
            distrorelease = DistroRelease.selectOneBy(
                distribution=self, version=name_or_version)
            if distrorelease is None:
                raise NotFoundError(name_or_version)
        return distrorelease

    def getDevelopmentReleases(self):
        """See IDistribution."""
        return DistroRelease.selectBy(
            distribution=self,
            releasestatus=DistributionReleaseStatus.DEVELOPMENT)

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

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None):
        """See IHasSpecifications.

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
            order = ['-priority', 'Specification.status', 'Specification.name']
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
            query += ' AND Specification.informational IS TRUE'

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
            query += ' AND Specification.status NOT IN ( %s, %s ) ' % \
                sqlvalues(SpecificationStatus.OBSOLETE,
                          SpecificationStatus.SUPERSEDED)

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
        return Specification.selectOneBy(distribution=self, name=name)

    def getSupportedLanguages(self):
        """See IQuestionTarget."""
        return get_supported_languages(self)

    def newQuestion(self, owner, title, description, language=None,
                  datecreated=None):
        """See IQuestionTarget."""
        return QuestionSet.new(
            title=title, description=description, owner=owner,
            distribution=self, datecreated=datecreated, language=language)

    def getQuestion(self, question_id):
        """See IQuestionTarget."""
        try:
            question = Question.get(question_id)
        except SQLObjectNotFound:
            return None
        # Verify that the question is actually for this distribution.
        if question.distribution != self:
            return None
        return question

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None):
        """See IQuestionTarget."""
        return QuestionTargetSearch(
            distribution=self,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from).getResults()


    def findSimilarQuestions(self, title):
        """See IQuestionTarget."""
        return SimilarQuestionsSearch(title, distribution=self).getResults()

    def addAnswerContact(self, person):
        """See IQuestionTarget."""
        if person in self.answer_contacts:
            return False
        AnswerContact(
            product=None, person=person,
            sourcepackagename=None, distribution=self)
        return True

    def removeAnswerContact(self, person):
        """See IQuestionTarget."""
        if person not in self.answer_contacts:
            return False
        answer_contact_entry = AnswerContact.selectOne(
            "distribution = %d AND person = %d"
            " AND sourcepackagename IS NULL" % (self.id, person.id))
        answer_contact_entry.destroySelf()
        return True

    @property
    def answer_contacts(self):
        """See IQuestionTarget."""
        answer_contacts = AnswerContact.select(
            """distribution = %d AND sourcepackagename IS NULL""" % self.id)

        return sorted(
            [answer_contact.person for answer_contact in answer_contacts],
            key=attrgetter('displayname'))

    @property
    def direct_answer_contacts(self):
        """See IQuestionTarget."""
        return self.answer_contacts

    def getQuestionLanguages(self):
        """See IQuestionTarget."""
        return set(Language.select(
            'Language.id = language AND distribution = %s AND '
            'sourcepackagename IS NULL' % sqlvalues(self),
            clauseTables=['Ticket'], distinct=True))

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
            candidate = SourcePackageFilePublishing.selectFirstBy(
                distribution=self, libraryfilealiasfilename=filename,
                orderBy=['id'])

        if binary:
            candidate = BinaryPackageFilePublishing.selectFirstBy(
                distribution=self,
                libraryfilealiasfilename=filename,
                orderBy=["-id"])

        if candidate is not None:
            return candidate.libraryfilealias

        raise NotFoundError(filename)

    def getBuildRecords(self, status=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        # Find out the distroarchreleases in question.
        arch_ids = []
        # concatenate architectures list since they are distinct.
        for release in self.releases:
            arch_ids += [arch.id for arch in release.architectures]

        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds(
            arch_ids, status, name, pocket)

    def removeOldCacheItems(self, log):
        """See IDistribution."""

        # Get the set of source package names to deal with.
        spns = set(SourcePackageName.select("""
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackagePublishingHistory.status != %s AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self, self.main_archive,
                            PackagePublishingStatus.REMOVED),
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
        """See IDistribution."""
        # Get the set of source package names to deal with.
        spns = list(SourcePackageName.select("""
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackagePublishingHistory.status != %s AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self, self.main_archive,
                            PackagePublishingStatus.REMOVED),
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
        """See IDistribution."""

        # Get the set of published sourcepackage releases.
        sprs = list(SourcePackageRelease.select("""
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackageRelease.id =
                SourcePackagePublishingHistory.sourcepackagerelease AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.status != %s
            """ % sqlvalues(sourcepackagename, self, self.main_archive,
                            PackagePublishingStatus.REMOVED),
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
        binpkgnames = set()
        binpkgsummaries = set()
        binpkgdescriptions = set()
        for spr in sprs:
            log.debug("Considering source version %s" % spr.version)
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

    def searchSourcePackages(self, text):
        """See IDistribution."""
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
        """See IDistribution"""
        assert isinstance(pkgname, basestring), (
            "Expected string. Got: %r" % pkgname)

        pkgname = pkgname.strip().lower()
        if not valid_name(pkgname):
            raise NotFoundError('Invalid package name: %s' % pkgname)

        if self.currentrelease is None:
            # Distribution with no releases can't have anything
            # published in it.
            raise NotFoundError('%s has no releases; %r was never '
                                'published in it'
                                % (self.displayname, pkgname))

        # The way this method works is that is tries to locate a pair of
        # packages related to that name. If it locates a binary package,
        # it then tries to find the source package most recently
        # associated with it, first in the current distrorelease and
        # then across the whole distribution. If it doesn't, it tries to
        # find a source package with that name published in the
        # distribution.
        #
        # XXX: note that the strategy of falling back to previous
        # distribution releases might be revisited in the future; for
        # instance, when people file bugs, it might actually be bad for
        # us to allow them to be associated with obsolete packages.
        #   -- kiko, 2006-07-28

        binarypackagename = BinaryPackageName.selectOneBy(name=pkgname)
        if binarypackagename:
            # Ok, so we have a binarypackage with that name. Grab its
            # latest publication -- first in the distribution release
            # and if that fails, in the distribution (this may be an old
            # package name the end-user is groping for) -- and then get
            # the sourcepackagename from that.
            publishing = PublishedPackage.selectFirstBy(
                binarypackagename=binarypackagename.name,
                distrorelease=self.currentrelease,
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

        sourcepackagename = SourcePackageName.selectOneBy(name=pkgname)
        if sourcepackagename is None:
            # Not a binary package name, not a source package name,
            # game over!
            if binarypackagename:
                raise NotFoundError('Binary package %s not published in %s'
                                    % (pkgname, self.displayname))
            else:
                raise NotFoundError('Unknown package: %s' % pkgname)

        # Note that in the source package case, we don't restrict
        # the search to the distribution release, making a best
        # effort to find a package.
        publishing = SourcePackagePublishingHistory.selectFirst('''
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.status = %s
            ''' % sqlvalues(self, self.main_archive, sourcepackagename,
                            PackagePublishingStatus.PUBLISHED),
            clauseTables=['SourcePackageRelease', 'DistroRelease'],
            distinct=True,
            orderBy="id")

        if publishing is None:
            raise NotFoundError('Package %s not published in %s'
                                % (pkgname, self.displayname))

        # Note the None here: if no source package was published for the
        # the binary package we found above, assume we ran into a red
        # herring and just ignore the binary package name hit.
        return (sourcepackagename, None)


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
        return iter(sorted(shortlist(distroset),
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
            members, owner, main_archive, gotchi, gotchi_heading, emblem):
        return Distribution(
            name=name,
            displayname=displayname,
            title=title,
            description=description,
            summary=summary,
            domainname=domainname,
            members=members,
            mirror_admin=owner,
            owner=owner,
            main_archive=main_archive,
            gotchi=gotchi,
            gotchi_heading=gotchi_heading,
            emblem=emblem)
