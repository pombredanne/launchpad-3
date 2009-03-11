# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212
"""Database classes that implement SourcePacakge items."""

__metaclass__ = type

__all__ = [
    'SourcePackage',
    'SourcePackageQuestionTargetMixin',
    ]

from operator import attrgetter
from warnings import warn
from sqlobject.sqlbuilder import SQLConstant
from zope.interface import implements

from storm.expr import And
from storm.store import Store

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates, sqlvalues
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.bug import get_bug_tags_open_count
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.distroseriessourcepackagerelease import (
    DistroSeriesSourcePackageRelease)
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.question import (
    QuestionTargetMixin, QuestionTargetSearch)
from canonical.launchpad.database.seriessourcepackagebranch import (
    SeriesSourcePackageBranch)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    BuildStatus, ISourcePackage, IHasBuildRecords, IHasTranslationTemplates,
    IQuestionTarget, PackagingType, PackagePublishingPocket,
    PackagePublishingStatus, QUESTION_STATUS_DEFAULT_SEARCH)


class SourcePackageQuestionTargetMixin(QuestionTargetMixin):
    """Implementation of IQuestionTarget for SourcePackage."""

    def getTargetTypes(self):
        """See `QuestionTargetMixin`.

        Defines distribution and sourcepackagename as this object's
        distribution and sourcepackagename.
        """
        return {'distribution': self.distribution,
                'sourcepackagename': self.sourcepackagename}

    def questionIsForTarget(self, question):
        """See `QuestionTargetMixin`.

        Return True when the question's distribution and sourcepackagename
        are this object's distribution and sourcepackagename.
        """
        if question.distribution is not self.distribution:
            return False
        if question.sourcepackagename is not self.sourcepackagename:
            return False
        return True

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
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from,
            unsupported_target=unsupported_target).getResults()

    def getAnswerContactsForLanguage(self, language):
        """See `IQuestionTarget`."""
        # Sourcepackages are supported by their distribtions too.
        persons = self.distribution.getAnswerContactsForLanguage(language)
        persons.update(QuestionTargetMixin.getAnswerContactsForLanguage(
            self, language))
        return sorted(
            [person for person in persons], key=attrgetter('displayname'))

    def getAnswerContactRecipients(self, language):
        """See `IQuestionTarget`."""
        # We need to special case the source package case because some are
        # contacts for the distro while others are only registered for the
        # package. And we also want the name of the package in context in
        # the header.
        recipients = self.distribution.getAnswerContactRecipients(language)
        recipients.update(QuestionTargetMixin.getAnswerContactRecipients(
            self, language))
        return recipients

    @property
    def _store(self):
        return Store.of(self.sourcepackagename)

    @property
    def answer_contacts(self):
        """See `IQuestionTarget`."""
        answer_contacts = set()
        answer_contacts.update(self.direct_answer_contacts)
        answer_contacts.update(self.distribution.answer_contacts)
        return sorted(answer_contacts, key=attrgetter('displayname'))

    @property
    def answer_contacts_with_languages(self):
        """Answer contacts with their languages pre-filled.

        Same as answer_contacts but with each answer contact having its
        languages pre-filled so that we don't need to hit the DB again to get
        them.
        """
        answer_contacts = set()
        answer_contacts.update(self.direct_answer_contacts_with_languages)
        answer_contacts.update(
            self.distribution.answer_contacts_with_languages)
        return sorted(answer_contacts, key=attrgetter('displayname'))


class SourcePackage(BugTargetBase, SourcePackageQuestionTargetMixin,
                    HasTranslationImportsMixin):
    """A source package, e.g. apache2, in a distroseries.

    This object is not a true database object, but rather attempts to
    represent the concept of a source package in a distro series, with links
    to the relevant database objects.
    """

    implements(
        ISourcePackage, IHasBuildRecords, IHasTranslationTemplates,
        IQuestionTarget)

    def __init__(self, sourcepackagename, distroseries):
        self.sourcepackagename = sourcepackagename
        self.distroseries = distroseries

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.path)

    def _get_ubuntu(self):
        # XXX: kiko 2006-03-20: Ideally, it would be possible to just do
        # ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        # and not need this method. However, importd currently depends
        # on SourcePackage methods that require the ubuntu celebrity,
        # and given it does not execute_zcml_for_scripts, we are forced
        # here to do this hack instead of using components. Ideally,
        # imports is rewritten to not use SourcePackage, or it
        # initializes the component architecture correctly.
        from canonical.launchpad.database.distribution import Distribution
        return Distribution.byName("ubuntu")

    def _getPublishingHistory(self, version=None, include_status=None,
                              exclude_status=None, order_by=None):
        """Build a query and return a list of SourcePackagePublishingHistory.

        This is mainly a helper function for this class so that code is
        not duplicated. include_status and exclude_status must be a sequence.
        """
        clauses = []
        clauses.append(
                """SourcePackagePublishingHistory.sourcepackagerelease =
                   SourcePackageRelease.id AND
                   SourcePackageRelease.sourcepackagename = %s AND
                   SourcePackagePublishingHistory.distroseries = %s AND
                   SourcePackagePublishingHistory.archive IN %s
                """ % sqlvalues(
                        self.sourcepackagename,
                        self.distroseries,
                        self.distribution.all_distro_archive_ids))
        if version:
            clauses.append(
                "SourcePackageRelease.version = %s" % sqlvalues(version))

        if include_status:
            if not isinstance(include_status, list):
                include_status = list(include_status)
            clauses.append("SourcePackagePublishingHistory.status IN %s"
                       % sqlvalues(include_status))

        if exclude_status:
            if not isinstance(exclude_status, list):
                exclude_status = list(exclude_status)
            clauses.append("SourcePackagePublishingHistory.status NOT IN %s"
                       % sqlvalues(exclude_status))

        query = " AND ".join(clauses)

        if not order_by:
            order_by = '-datepublished'

        return SourcePackagePublishingHistory.select(
            query, orderBy=order_by, clauseTables=['SourcePackageRelease'],
            prejoinClauseTables=['SourcePackageRelease'])

    def _getFirstPublishingHistory(self, version=None, include_status=None,
                                   exclude_status=None, order_by=None):
        """As _getPublishingHistory, but just returns the first item."""
        try:
            package = self._getPublishingHistory(
                version, include_status, exclude_status, order_by)[0]
        except IndexError:
            return None
        else:
            return package

    @property
    def currentrelease(self):
        releases = self.distroseries.getCurrentSourceReleases(
            [self.sourcepackagename])
        return releases.get(self)

    def __getitem__(self, version):
        """See `ISourcePackage`."""
        latest_package = self._getFirstPublishingHistory(version=version)
        if latest_package:
            return DistroSeriesSourcePackageRelease(
                    self.distroseries, latest_package.sourcepackagerelease)
        else:
            return None

    @property
    def path(self):
        """See `ISourcePackage`."""
        return '/'.join([
            self.distribution.name,
            self.distroseries.name,
            self.sourcepackagename.name])

    @property
    def displayname(self):
        return "%s %s %s" % (
            self.distribution.displayname,
            self.distroseries.displayname, self.sourcepackagename.name)

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return "%s (%s)" % (self.name, self.distroseries.fullseriesname)

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return "%s (%s)" % (self.name, self.distroseries.fullseriesname)

    @property
    def title(self):
        titlestr = self.sourcepackagename.name
        titlestr += ' in ' + self.distribution.displayname
        titlestr += ' ' + self.distroseries.displayname
        return titlestr

    @property
    def distribution(self):
        return self.distroseries.distribution

    @property
    def format(self):
        if not self.currentrelease:
            return None
        return self.currentrelease.format

    @property
    def releases(self):
        """See `ISourcePackage`."""
        order_const = "debversion_sort_key(SourcePackageRelease.version)"
        packages = self._getPublishingHistory(
            order_by=[SQLConstant(order_const),
                      "SourcePackagePublishingHistory.datepublished"])

        return [DistributionSourcePackageRelease(
                distribution=self.distribution,
                sourcepackagerelease=package.sourcepackagerelease)
                   for package in packages]

    @property
    def distinctreleases(self):
        """Return all distinct `SourcePackageReleases` for this sourcepackage.

        The results are ordered by descending version.
        """
        query = """
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.archive IN %s
        """ % sqlvalues(self.sourcepackagename, self.distribution,
                            self.distribution.all_distro_archive_ids)

        clauseTables = ['DistroSeries', 'SourcePackagePublishingHistory']
        order_const = "debversion_sort_key(SourcePackageRelease.version)"

        # Selecting ordered distinct `SourcePackageReleases` requires us
        # to 'selectAlso' the ordering index (the debversion_sort_key).
        releases = SourcePackageRelease.select(
            query, clauseTables=clauseTables,
            distinct=True, selectAlso=order_const,
            orderBy=[SQLConstant(order_const + " DESC")])

        return releases

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def product(self):
        # we have moved to focusing on productseries as the linker
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
        """See `ISourcePackage`."""
        # XXX flacoste 2008-02-28 For some crack reasons, it is possible
        # for multiple productseries (of the same product) to state that they
        # are packaged in the same source package. This creates all sort of
        # weirdness documented in bug #196774. But in order to work around bug
        # #181770, use a sort order that will be stable. I guess it makes the
        # most sense to return the latest one.
        return Packaging.selectFirstBy(
            sourcepackagename=self.sourcepackagename,
            distroseries=self.distroseries,
            orderBy=['packaging', '-datecreated'])

    @property
    def packaging(self):
        """See `ISourcePackage`"""
        # First we look to see if there is packaging data for this
        # distroseries and sourcepackagename. If not, we look up through
        # parent distroserieses, and when we hit Ubuntu, we look backwards in
        # time through Ubuntu series till we find packaging information or
        # blow past the Warty Warthog.

        # see if there is a direct packaging
        result = self.direct_packaging
        if result is not None:
            return result

        ubuntu = self._get_ubuntu()
        # if we are an ubuntu sourcepackage, try the previous series of
        # ubuntu
        if self.distribution == ubuntu:
            ubuntuserieses = self.distroseries.previous_serieses
            if ubuntuserieses:
                previous_ubuntu_series = ubuntuserieses[0]
                sp = SourcePackage(sourcepackagename=self.sourcepackagename,
                                   distroseries=previous_ubuntu_series)
                return sp.packaging
        # if we have a parent distroseries, try that
        if self.distroseries.parent_series is not None:
            sp = SourcePackage(sourcepackagename=self.sourcepackagename,
                               distroseries=self.distroseries.parent_series)
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

        ubuntu = self._get_ubuntu()
        if self.distribution != ubuntu:
            return False
        ps = self.productseries
        if ps is None:
            return False
        return ps.import_branch is not None

    @property
    def published_by_pocket(self):
        """See `ISourcePackage`."""
        result = self._getPublishingHistory(
            include_status=[PackagePublishingStatus.PUBLISHED])
        # create the dictionary with the set of pockets as keys
        thedict = {}
        for pocket in PackagePublishingPocket.items:
            thedict[pocket] = []
        # add all the sourcepackagereleases in the right place
        for spr in result:
            thedict[spr.pocket].append(DistroSeriesSourcePackageRelease(
                spr.distroseries, spr.sourcepackagerelease))
        return thedict

    @property
    def bug_reporting_guidelines(self):
        """See `IBugTarget`."""
        return self.distribution.bug_reporting_guidelines

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this source package."""
        search_params.setSourcePackage(self)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        return self.distroseries.getUsedBugTags()

    def getUsedBugTagsWithOpenCounts(self, user):
        """See `IBugTarget`."""
        return get_bug_tags_open_count(
            And(BugTask.distroseries == self.distroseries,
                BugTask.sourcepackagename == self.sourcepackagename),
            user)

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug directly on an
        # ISourcePackage, because internally ISourcePackage bugs mean bugs
        # targeted to be fixed in a specific distroseries + sourcepackage.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a source package in a "
            "specific distribution series, because series are meant for "
            "\"targeting\" a fix to a specific series. It's possible that "
            "we may change this behaviour to allow filing a bug on a "
            "distribution series source package in the not-too-distant "
            "future. For now, you probably meant to file the bug on the "
            "distro-wide (i.e. not series-specific) source package.")

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return (
            'BugTask.distroseries = %s AND BugTask.sourcepackagename = %s' %
                sqlvalues(self.distroseries, self.sourcepackagename))

    def setPackaging(self, productseries, user):
        target = self.direct_packaging
        if target is not None:
            # we should update the current packaging
            target.productseries = productseries
            target.owner = user
            target.datecreated = UTC_NOW
        else:
            # ok, we need to create a new one
            Packaging(distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename,
            productseries=productseries, owner=user,
            packaging=PackagingType.PRIME)
        # and make sure this change is immediately available
        flush_database_updates()

    def __hash__(self):
        """See `ISourcePackage`."""
        return hash(self.distroseries.id) ^ hash(self.sourcepackagename.id)

    def __eq__(self, other):
        """See `ISourcePackage`."""
        return (
            (ISourcePackage.providedBy(other)) and
            (self.distroseries.id == other.distroseries.id) and
            (self.sourcepackagename.id == other.sourcepackagename.id))

    def __ne__(self, other):
        """See `ISourcePackage`."""
        return not self.__eq__(other)

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        user=None):
        # Ignore "user", since it would not make any difference to the
        # records returned here (private builds are only in PPA right
        # now and this method only returns records for SPRs in a
        # distribution).

        """See `IHasBuildRecords`"""
        clauseTables = ['SourcePackageRelease',
                        'SourcePackagePublishingHistory']

        condition_clauses = ["""
        Build.sourcepackagerelease = SourcePackageRelease.id AND
        SourcePackageRelease.sourcepackagename = %s AND
        SourcePackagePublishingHistory.distroseries = %s AND
        SourcePackagePublishingHistory.archive IN %s AND
        SourcePackagePublishingHistory.sourcepackagerelease =
        SourcePackageRelease.id
        """ % sqlvalues(self.sourcepackagename,
                        self.distroseries,
                        self.distribution.all_distro_archive_ids)]

        # XXX cprov 2006-09-25: It would be nice if we could encapsulate
        # the chunk of code below (which deals with the optional paramenters)
        # and share it with IBuildSet.getBuildsByArchIds()

        # exclude gina-generated and security (dak-made) builds
        # buildstate == FULLYBUILT && datebuilt == null
        condition_clauses.append(
            "NOT (Build.buildstate=%s AND Build.datebuilt is NULL)"
            % sqlvalues(BuildStatus.FULLYBUILT))

        if build_state is not None:
            condition_clauses.append("Build.buildstate=%s"
                                     % sqlvalues(build_state))

        if pocket:
            condition_clauses.append(
                "Build.pocket = %s" % sqlvalues(pocket))

        # Ordering according status
        # * NEEDSBUILD & BUILDING by -lastscore
        # * SUPERSEDED by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if build_state in [BuildStatus.NEEDSBUILD, BuildStatus.BUILDING]:
            orderBy = ["-BuildQueue.lastscore"]
            clauseTables.append('BuildQueue')
            condition_clauses.append('BuildQueue.build = Build.id')
        elif build_state == BuildStatus.SUPERSEDED or build_state is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # Fallback to ordering by -id as a tie-breaker.
        orderBy.append("-id")

        # End of duplication (see XXX cprov 2006-09-25 above).

        return Build.select(' AND '.join(condition_clauses),
                            clauseTables=clauseTables, orderBy=orderBy)

    @property
    def latest_published_component(self):
        """See `ISourcePackage`."""
        latest_publishing = self._getFirstPublishingHistory(
            include_status=[PackagePublishingStatus.PUBLISHED])
        if latest_publishing is not None:
            return latest_publishing.component
        else:
            return None

    def getTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.selectBy(
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)
        return shortlist(result.orderBy(['-priority', 'name']), 300)

    def getCurrentTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            distroseries = %s AND
            sourcepackagename = %s AND
            iscurrent IS TRUE AND
            distroseries = DistroSeries.id AND
            DistroSeries.distribution = Distribution.id AND
            Distribution.official_rosetta IS TRUE
            ''' % sqlvalues(self.distroseries, self.sourcepackagename),
            clauseTables = ['DistroSeries', 'Distribution'])
        return shortlist(result.orderBy(['-priority', 'name']), 300)

    def getObsoleteTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            distroseries = %s AND
            sourcepackagename = %s AND
            distroseries = DistroSeries.id AND
            DistroSeries.distribution = Distribution.id AND
            (iscurrent IS FALSE OR Distribution.official_rosetta IS FALSE)
            ''' % sqlvalues(self.distroseries, self.sourcepackagename),
            clauseTables = ['DistroSeries', 'Distribution'])
        return shortlist(result.orderBy(['-priority', 'name']), 300)

    def getBranch(self, pocket):
        store = Store.of(self.sourcepackagename)
        return store.find(
            Branch,
            SeriesSourcePackageBranch.distroseries == self.distroseries.id,
            (SeriesSourcePackageBranch.sourcepackagename
             == self.sourcepackagename.id),
            SeriesSourcePackageBranch.pocket == pocket,
            SeriesSourcePackageBranch.branch == Branch.id).one()
