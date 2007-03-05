# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'SourcePackage',
    'SourcePackageQuestionTargetMixin',
    ]

from operator import attrgetter
from warnings import warn

from zope.interface import implements

from sqlobject import SQLObjectNotFound
from sqlobject.sqlbuilder import SQLConstant

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates, sqlvalues

from canonical.lp.dbschema import (
    PackagingType, PackagePublishingPocket, BuildStatus,
    PackagePublishingStatus)

from canonical.launchpad.interfaces import (
    ISourcePackage, IHasBuildRecords, IQuestionTarget,
    get_supported_languages, QUESTION_STATUS_DEFAULT_SEARCH)
from canonical.launchpad.database.bugtarget import BugTargetBase

from canonical.launchpad.database.answercontact import AnswerContact
from canonical.launchpad.database.bug import get_bug_tags_open_count
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.question import (
    SimilarQuestionsSearch, Question, QuestionTargetSearch, QuestionSet)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease)
from canonical.launchpad.database.distroreleasesourcepackagerelease import (
    DistroReleaseSourcePackageRelease)
from canonical.launchpad.database.build import Build


class SourcePackageQuestionTargetMixin:
    """Implementation of IQuestionTarget for SourcePackage."""

    def newQuestion(self, owner, title, description, language=None,
                    datecreated=None):
        """See IQuestionTarget."""
        return QuestionSet.new(
            title=title, description=description, owner=owner,
            language=language, distribution=self.distribution,
            sourcepackagename=self.sourcepackagename, datecreated=datecreated)

    def getQuestion(self, question_id):
        """See IQuestionTarget."""
        try:
            question = Question.get(question_id)
        except SQLObjectNotFound:
            return None
        # Verify that this question is actually for this target.
        if question.distribution != self.distribution:
            return None
        if question.sourcepackagename != self.sourcepackagename:
            return None
        return question

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None):
        """See IQuestionTarget."""
        return QuestionTargetSearch(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from).getResults()

    def findSimilarQuestions(self, title):
        """See IQuestionTarget."""
        return SimilarQuestionsSearch(
            title, distribution=self.distribution,
            sourcepackagename=self.sourcepackagename).getResults()

    def addAnswerContact(self, person):
        """See IQuestionTarget."""
        answer_contact_entry = AnswerContact.selectOneBy(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            person=person)
        if answer_contact_entry:
            return False

        AnswerContact(
            product=None, person=person,
            sourcepackagename=self.sourcepackagename,
            distribution=self.distribution)
        return True

    def removeAnswerContact(self, person):
        """See IQuestionTarget."""
        answer_contact_entry = AnswerContact.selectOneBy(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename,
            person=person)
        if not answer_contact_entry:
            return False

        answer_contact_entry.destroySelf()
        return True

    @property
    def answer_contacts(self):
        """See IQuestionTarget."""
        answer_contacts = set()
        answer_contacts.update(self.direct_answer_contacts)
        answer_contacts.update(self.distribution.answer_contacts)
        return sorted(answer_contacts, key=attrgetter('displayname'))

    @property
    def direct_answer_contacts(self):
        """See IQuestionTarget."""
        answer_contacts = AnswerContact.selectBy(
            distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)
        return sorted(
            [contact.person for contact in answer_contacts],
            key=attrgetter('displayname'))

    def getSupportedLanguages(self):
        """See IQuestionTarget."""
        return get_supported_languages(self)

    def getQuestionLanguages(self):
        """See IQuestionTarget."""
        return set(Language.select(
            'Language.id = language AND distribution = %s AND '
            'sourcepackagename = %s'
                % sqlvalues(self.distribution, self.sourcepackagename),
            clauseTables=['Ticket'], distinct=True))



class SourcePackage(BugTargetBase, SourcePackageQuestionTargetMixin):
    """A source package, e.g. apache2, in a distrorelease.

    This object implements the MagicSourcePackage specification. It is not a
    true database object, but rather attempts to represent the concept of a
    source package in a distro release, with links to the relevant database
    objects.
    """

    implements(ISourcePackage, IHasBuildRecords, IQuestionTarget)

    def __init__(self, sourcepackagename, distrorelease):
        self.sourcepackagename = sourcepackagename
        self.distrorelease = distrorelease

    def _get_ubuntu(self):
        # XXX: Ideally, it would be possible to just do
        # ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        # and not need this method. However, importd currently depends
        # on SourcePackage methods that require the ubuntu celebrity,
        # and given it does not execute_zcml_for_scripts, we are forced
        # here to do this hack instead of using components. Ideally,
        # imports is rewritten to not use SourcePackage, or it
        # initializes the component architecture correctly.
        from canonical.launchpad.database.distribution import Distribution
        return Distribution.byName("ubuntu")

    @property
    def currentrelease(self):
        pkg = SourcePackagePublishingHistory.selectFirst("""
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.status != %s
            """ % sqlvalues(self.sourcepackagename,
                            self.distrorelease,
                            self.distrorelease.main_archive,
                            PackagePublishingStatus.REMOVED),
            orderBy='-datepublished',
            clauseTables=['SourcePackageRelease'])
        if pkg is None:
            return None
        currentrelease = DistroReleaseSourcePackageRelease(
            distrorelease=self.distrorelease,
            sourcepackagerelease=pkg.sourcepackagerelease)
        return currentrelease

    def __getitem__(self, version):
        """See ISourcePackage."""
        pkg = SourcePackagePublishingHistory.selectFirst("""
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.version = %s AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.status != %s
            """ % sqlvalues(version, self.sourcepackagename,
                            self.distrorelease,
                            self.distrorelease.main_archive,
                            PackagePublishingStatus.REMOVED),
            orderBy='-datepublished',
            clauseTables=['SourcePackageRelease'])
        if pkg is None:
            return None
        return DistroReleaseSourcePackageRelease(
            self.distrorelease, pkg.sourcepackagerelease)

    @property
    def displayname(self):
        return "%s %s" % (
            self.distrorelease.displayname, self.sourcepackagename.name)

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return "%s (%s)" % (self.name, self.distrorelease.fullreleasename)

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
    def format(self):
        if not self.currentrelease:
            return None
        return self.currentrelease.format

    # XXX: should not be a property -- kiko, 2006-08-16
    @property
    def changelog(self):
        """See ISourcePackage"""

        clauseTables = ('SourcePackageName', 'SourcePackageRelease',
                        'SourcePackagePublishingHistory','DistroRelease')

        query = """
        SourcePackageRelease.sourcepackagename =
           SourcePackageName.id AND
        SourcePackageName = %s AND
        SourcePackagePublishingHistory.distrorelease =
           DistroRelease.Id AND
        SourcePackagePublishingHistory.distrorelease = %s AND
        SourcePackagePublishingHistory.archive = %s AND
        SourcePackagePublishingHistory.status != %s AND
        SourcePackagePublishingHistory.sourcepackagerelease =
           SourcePackageRelease.id
        """ % sqlvalues(self.sourcepackagename,
                        self.distrorelease,
                        self.distrorelease.main_archive,
                        PackagePublishingStatus.REMOVED)

        spreleases = SourcePackageRelease.select(
            query, clauseTables=clauseTables, orderBy='version').reversed()
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
    def releases(self):
        """See ISourcePackage."""
        order_const = "debversion_sort_key(SourcePackageRelease.version)"
        releases = SourcePackageRelease.select('''
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.status != %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id
            ''' % sqlvalues(self.sourcepackagename,
                            self.distrorelease,
                            self.distrorelease.main_archive,
                            PackagePublishingStatus.REMOVED),
            clauseTables=['SourcePackagePublishingHistory'],
            orderBy=[SQLConstant(order_const),
                     "SourcePackagePublishingHistory.datepublished"])

        return [DistributionSourcePackageRelease(
                distribution=self.distribution,
                sourcepackagerelease=release) for release in releases]

    @property
    def releasehistory(self):
        """See ISourcePackage."""
        order_const = "debversion_sort_key(SourcePackageRelease.version)"
        releases = SourcePackageRelease.select('''
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.distrorelease =
                DistroRelease.id AND
            DistroRelease.distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.status != %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id
            ''' % sqlvalues(self.sourcepackagename,
                            self.distribution,
                            self.distribution.main_archive,
                            PackagePublishingStatus.REMOVED),
            clauseTables=['DistroRelease', 'SourcePackagePublishingHistory'],
            orderBy=[SQLConstant(order_const),
                     "SourcePackagePublishingHistory.datepublished"])
        return releases

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def potemplates(self):
        result = POTemplate.selectBy(
            distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename)
        return sorted(list(result), key=lambda x: x.potemplatename.name)

    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(
            distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename,
            iscurrent=True)
        return sorted(list(result), key=lambda x: x.potemplatename.name)

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
        """See ISourcePackage."""
        # get any packagings matching this sourcepackage
        return Packaging.selectFirstBy(
            sourcepackagename=self.sourcepackagename,
            distrorelease=self.distrorelease,
            orderBy='packaging')

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

        ubuntu = self._get_ubuntu()
        # if we are an ubuntu sourcepackage, try the previous release of
        # ubuntu
        if self.distribution == ubuntu:
            ubuntureleases = self.distrorelease.previous_releases
            if ubuntureleases:
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

        ubuntu = self._get_ubuntu()
        if self.distribution != ubuntu:
            return False
        ps = self.productseries
        if ps is None:
            return False
        return ps.import_branch is not None

    @property
    def published_by_pocket(self):
        """See ISourcePackage."""
        result = SourcePackagePublishingHistory.select("""
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename = %s AND
            SourcePackagePublishingHistory.status != %s
            """ % sqlvalues(self.distrorelease,
                            self.distrorelease.main_archive,
                            self.sourcepackagename,
                            PackagePublishingStatus.REMOVED),
            clauseTables=['SourcePackageRelease'])
        # create the dictionary with the set of pockets as keys
        thedict = {}
        for pocket in PackagePublishingPocket.items:
            thedict[pocket] = []
        # add all the sourcepackagereleases in the right place
        for spr in result:
            thedict[spr.pocket].append(DistroReleaseSourcePackageRelease(
                spr.distrorelease, spr.sourcepackagerelease))
        return thedict

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setSourcePackage(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return self.distrorelease.getUsedBugTags()

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.distrorelease = %s" % sqlvalues(self.distrorelease),
            user,
            count_subcontext_clause="BugTask.sourcepackagename = %s" % (
                sqlvalues(self.sourcepackagename)))

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug directly on an
        # ISourcePackage, because internally ISourcePackage bugs mean bugs
        # targetted to be fixed in a specific distrorelease + sourcepackage.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a source package in a "
            "specific distribution release, because releases are meant for "
            "\"targeting\" a fix to a specific release. It's possible that "
            "we may change this behaviour to allow filing a bug on a "
            "distribution release source package in the not-too-distant "
            "future. For now, you probably meant to file the bug on the "
            "distro-wide (i.e. not release-specific) source package.")

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return (
            'BugTask.distrorelease = %s AND BugTask.sourcepackagename = %s' %
                sqlvalues(self.distrorelease, self.sourcepackagename))

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

    def __eq__(self, other):
        """See canonical.launchpad.interfaces.ISourcePackage."""
        return (
            (ISourcePackage.providedBy(other)) and
            (self.distrorelease.id == other.distrorelease.id) and
            (self.sourcepackagename.id == other.sourcepackagename.id))

    def __ne__(self, other):
        """See canonical.launchpad.interfaces.ISourcePackage."""
        return not self.__eq__(other)

    def getBuildRecords(self, status=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        clauseTables = ['SourcePackageRelease',
                        'SourcePackagePublishingHistory']

        condition_clauses = ["""
        Build.sourcepackagerelease = SourcePackageRelease.id AND
        SourcePackageRelease.sourcepackagename = %s AND
        SourcePackagePublishingHistory.distrorelease = %s AND
        SourcePackagePublishingHistory.archive = %s AND
        SourcePackagePublishingHistory.status = %s AND
        SourcePackagePublishingHistory.sourcepackagerelease =
        SourcePackageRelease.id
        """ % sqlvalues(self.sourcepackagename,
                        self.distrorelease,
                        self.distrorelease.main_archive,
                        PackagePublishingStatus.PUBLISHED)]

        # XXX cprov 20060925: It would be nice if we could encapsulate
        # the chunk of code below (which deals with the optional paramenters)
        # and share it with IBuildSet.getBuildsByArchIds()

        # exclude gina-generated and security (dak-made) builds
        # buildstate == FULLYBUILT && datebuilt == null
        condition_clauses.append(
            "NOT (Build.buildstate=%s AND Build.datebuilt is NULL)"
            % sqlvalues(BuildStatus.FULLYBUILT))

        if status is not None:
            condition_clauses.append("Build.buildstate=%s"
                                     % sqlvalues(status))

        if pocket:
            condition_clauses.append(
                "Build.pocket = %s" % sqlvalues(pocket))

        # Ordering according status
        # * NEEDSBUILD & BUILDING by -lastscore
        # * SUPERSEDED by -datecreated
        # * FULLYBUILT & FAILURES by -datebuilt
        # It should present the builds in a more natural order.
        if status in [BuildStatus.NEEDSBUILD, BuildStatus.BUILDING]:
            orderBy = ["-BuildQueue.lastscore"]
            clauseTables.append('BuildQueue')
            condition_clauses.append('BuildQueue.build = Build.id')
        elif status == BuildStatus.SUPERSEDED or status is None:
            orderBy = ["-Build.datecreated"]
        else:
            orderBy = ["-Build.datebuilt"]

        # Fallback to ordering by -id as a tie-breaker.
        orderBy.append("-id")

        # End of duplication (see XXX cprov 20060925 above).

        return Build.select(' AND '.join(condition_clauses),
                            clauseTables=clauseTables, orderBy=orderBy)
