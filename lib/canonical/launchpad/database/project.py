# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Launchpad Project-related Database Table Objects."""

__metaclass__ = type
__all__ = [
    'Project',
    'ProjectSet',
    ]

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLObjectNotFound, SQLRelatedJoin)

from canonical.database.sqlbase import cursor, SQLBase, sqlvalues, quote
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    ICalendarOwner, IFAQCollection, IHasIcon, IHasLogo, IHasMugshot, IProduct,
    IProject, IProjectSet, ISearchableByQuestionOwner, NotFoundError,
    QUESTION_STATUS_DEFAULT_SEARCH, TranslationPermission)

from canonical.lp.dbschema import (
    ImportStatus, SpecificationSort, SpecificationFilter,
    SprintSpecificationStatus, SpecificationImplementationStatus)

from canonical.launchpad.database.branchvisibilitypolicy import (
    BranchVisibilityPolicyMixin)
from canonical.launchpad.database.bug import (
    get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.cal import Calendar
from canonical.launchpad.database.faq import FAQ, FAQSearch
from canonical.launchpad.database.karma import KarmaContextMixin
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.milestone import ProjectMilestone
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.projectbounty import ProjectBounty
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.sprint import HasSprintsMixin
from canonical.launchpad.database.question import QuestionTargetSearch
from canonical.launchpad.helpers import shortlist


class Project(SQLBase, BugTargetBase, HasSpecificationsMixin,
              HasSprintsMixin, KarmaContextMixin,
              BranchVisibilityPolicyMixin):
    """A Project"""

    implements(ICalendarOwner, IProject, IFAQCollection, IHasIcon, IHasLogo,
               IHasMugshot, ISearchableByQuestionOwner)

    _table = "Project"

    # db field names
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    summary = StringCol(dbName='summary', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=True,
        default=UTC_NOW)
    driver = ForeignKey(
        foreignKey="Person", dbName="driver", notNull=False, default=None)
    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
    wikiurl = StringCol(dbName='wikiurl', notNull=False, default=None)
    sourceforgeproject = StringCol(dbName='sourceforgeproject', notNull=False,
        default=None)
    freshmeatproject = StringCol(dbName='freshmeatproject', notNull=False,
        default=None)
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=False, default=None)
    translationpermission = EnumCol(dbName='translationpermission',
        notNull=True, schema=TranslationPermission,
        default=TranslationPermission.OPEN)
    active = BoolCol(dbName='active', notNull=True, default=True)
    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    bugtracker = ForeignKey(
        foreignKey="BugTracker", dbName="bugtracker", notNull=False,
        default=None)

    # convenient joins

    bounties = SQLRelatedJoin('Bounty', joinColumn='project',
                            otherColumn='bounty',
                            intermediateTable='ProjectBounty')

    calendar = ForeignKey(dbName='calendar', foreignKey='Calendar',
                          default=None, forceDBName=True)

    @property
    def products(self):
        return Product.selectBy(project=self, active=True, orderBy='name')

    def getOrCreateCalendar(self):
        if not self.calendar:
            self.calendar = Calendar(
                title='%s Project Calendar' % self.displayname,
                revision=0)
        return self.calendar

    def getProduct(self, name):
        return Product.selectOneBy(project=self, name=name)

    def ensureRelatedBounty(self, bounty):
        """See `IProject`."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        ProjectBounty(project=self, bounty=bounty)
        return None

    @property
    def mentoring_offers(self):
        """See `IProject`"""
        via_specs = MentoringOffer.select("""
            Product.project = %s AND
            Specification.product = Product.id AND
            Specification.id = MentoringOffer.specification
            """ % sqlvalues(self.id) + """ AND NOT
            (""" + Specification.completeness_clause +")",
            clauseTables=['Product', 'Specification'],
            distinct=True)
        via_bugs = MentoringOffer.select("""
            Product.project = %s AND
            BugTask.product = Product.id AND
            BugTask.bug = MentoringOffer.bug AND
            BugTask.bug = Bug.id AND
            Bug.private IS FALSE
            """ % sqlvalues(self.id) + """ AND NOT (
            """ + BugTask.completeness_clause + ")",
            clauseTables=['Product', 'BugTask', 'Bug'],
            distinct=True)
        return via_specs.union(via_bugs, orderBy=['-date_created', '-id'])

    def translatables(self):
        """See `IProject`."""
        return Product.select('''
            Product.project = %s AND
            Product.official_rosetta = TRUE AND
            Product.id = ProductSeries.product AND
            POTemplate.productseries = ProductSeries.id
            ''' % sqlvalues(self),
            clauseTables=['ProductSeries', 'POTemplate'],
            distinct=True)

    def _getBaseQueryAndClauseTablesForQueryingSprints(self):
        query = """
            Product.project = %s
            AND Specification.product = Product.id
            AND Specification.id = SprintSpecification.specification
            AND SprintSpecification.sprint = Sprint.id
            AND SprintSpecification.status = %s
            """ % sqlvalues(self, SprintSpecificationStatus.ACCEPTED)
        return query, ['Product', 'Specification', 'SprintSpecification']

    @property
    def has_any_specifications(self):
        """See `IHasSpecifications`."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    @property
    def valid_specifications(self):
        return self.specifications(filter=[SpecificationFilter.VALID])

    def specifications(self, sort=None, quantity=None, filter=None):
        """See `IHasSpecifications`."""

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a project is to show incomplete specs
            filter = [SpecificationFilter.INCOMPLETE]

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = (
                ['-priority', 'Specification.definition_status', 'Specification.name'])
        elif sort == SpecificationSort.DATE:
            order = ['-Specification.datecreated', 'Specification.id']

        # figure out what set of specifications we are interested in. for
        # projects, we need to be able to filter on the basis of:
        #
        #  - completeness. by default, only incomplete specs shown
        #  - informational.
        #
        base = """
            Specification.product = Product.id AND
            Product.active IS TRUE AND
            Product.project = %s
            """ % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
              quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

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
        results = Specification.select(query, orderBy=order, limit=quantity,
            clauseTables=['Product'])
        return results.prejoin(['assignee', 'approver', 'drafter'])

    # XXX: Bjorn Tillenius 2006-08-17:
    #      A Project shouldn't provide IBugTarget, since it's not really
    #      a bug target, thus bugtargetdisplayname and createBug don't make
    #      sense here. IBugTarget should be split into two interfaces; one
    #      that makes sense for Project to implement, and one containing the
    #      rest of IBugTarget.
    bugtargetdisplayname = None

    def searchTasks(self, search_params):
        """See `IBugTarget`."""
        search_params.setProject(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        if not self.products:
            return []
        product_ids = sqlvalues(*self.products)
        return get_bug_tags(
            "BugTask.product IN (%s)" % ",".join(product_ids))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See `IBugTarget`."""
        if not self.products:
            return []
        product_ids = sqlvalues(*self.products)
        return get_bug_tags_open_count(
            "BugTask.product IN (%s)" % ",".join(product_ids), user)

    def createBug(self, bug_params):
        """See `IBugTarget`."""
        raise NotImplementedError('Cannot file bugs against a project')

    def _getBugTaskContextClause(self):
        """See `BugTargetBase`."""
        return 'BugTask.product IN (%s)' % ','.join(sqlvalues(*self.products))

    # IQuestionCollection
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
            project=self,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from,
            unsupported_target=unsupported_target).getResults()

    def getQuestionLanguages(self):
        """See `IQuestionCollection`."""
        return set(Language.select("""
            Language.id = Question.language AND
            Question.product = Product.id AND
            Product.project = %s""" % sqlvalues(self.id),
            clauseTables=['Question', 'Product'], distinct=True))

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.displayname

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return self.name

    # IFAQCollection
    def getFAQ(self, id):
        """See `IQuestionCollection`."""
        faq = FAQ.getForTarget(id, None)
        if (faq is not None
            and IProduct.providedBy(faq.target)
            and faq.target in self.products):
            # Filter out faq not related to this project.
            return faq
        else:
            return None

    def searchFAQs(self, search_text=None, owner=None, sort=None):
        """See `IQuestionCollection`."""
        return FAQSearch(
            search_text=search_text, owner=owner, sort=sort,
            project=self).getResults()

    def hasProducts(self):
        """Returns True if a project has products associated with it, False
        otherwise.

        If the project has < 1 product, selected links will be disabled.
        This is to avoid situations where users try to file bugs against
        empty project groups (Malone bug #106523).
        """
        return self.products.count() != 0

    def _getMilestones(self, only_visible):
        """Return a list of milestones for this project.

        If only_visible is True, only visible milestones are returned,
        else all milestones.

        A project has a milestone named 'A', if at least one of its
        products has a milestone named 'A'.
        """
        if only_visible:
            having_clause = 'HAVING bool_or(Milestone.visible)=True'
        else:
            having_clause = ''
        query = """
            SELECT Milestone.name, min(Milestone.dateexpected),
                bool_or(Milestone.visible)
                FROM Milestone, Product
                WHERE Product.project = %s
                    AND Milestone.product = product.id
                GROUP BY Milestone.name
                %s
                ORDER BY min(Milestone.dateexpected), Milestone.name
            """ % (self.id, having_clause)
        cur = cursor()
        cur.execute(query)
        result = cur.fetchall()
        # bool_or returns an integer, but we want visible to be a boolean
        return shortlist(
            [ProjectMilestone(self, name, dateexpected, bool(visible))
             for name, dateexpected, visible in result])

    @property
    def milestones(self):
        """See `IProject`."""
        return self._getMilestones(True)

    @property
    def all_milestones(self):
        """See `IProject`."""
        return self._getMilestones(False)

    def getMilestone(self, name):
        """See `IProject`."""
        for milestone in self.all_milestones:
            if milestone.name == name:
                return milestone
        return None

class ProjectSet:
    implements(IProjectSet)

    def __init__(self):
        self.title = 'Projects registered in Launchpad'

    def __iter__(self):
        return iter(Project.selectBy(active=True))

    def __getitem__(self, name):
        project = Project.selectOneBy(name=name, active=True)
        if project is None:
            raise NotFoundError(name)
        return project

    def get(self, projectid):
        """See `canonical.launchpad.interfaces.project.IProjectSet`.

        >>> getUtility(IProjectSet).get(1).name
        u'apache'
        >>> getUtility(IProjectSet).get(-1)
        Traceback (most recent call last):
        ...
        NotFoundError: -1
        """
        try:
            project = Project.get(projectid)
        except SQLObjectNotFound:
            raise NotFoundError(projectid)
        return project

    def getByName(self, name, default=None, ignore_inactive=False):
        """See `canonical.launchpad.interfaces.project.IProjectSet`."""
        if ignore_inactive:
            project = Project.selectOneBy(name=name, active=True)
        else:
            project = Project.selectOneBy(name=name)
        if project is None:
            return default
        return project

    def new(self, name, displayname, title, homepageurl, summary,
            description, owner, mugshot=None, logo=None, icon=None):
        """See `canonical.launchpad.interfaces.project.IProjectSet`."""
        return Project(
            name=name,
            displayname=displayname,
            title=title,
            summary=summary,
            description=description,
            homepageurl=homepageurl,
            owner=owner,
            datecreated=UTC_NOW,
            mugshot=mugshot,
            logo=logo,
            icon=icon)

    def count_all(self):
        return Project.select().count()

    def forReview(self):
        return Project.select("reviewed IS FALSE")

    def forSyncReview(self):
        query = """Product.project=Project.id AND
                   Product.reviewed IS TRUE AND
                   Product.active IS TRUE AND
                   Product.id=ProductSeries.product AND
                   ProductSeries.importstatus IS NOT NULL AND
                   ProductSeries.importstatus <> %s
                   """ % sqlvalues(ImportStatus.SYNCING)
        clauseTables = ['Project', 'Product', 'ProductSeries']
        results = []
        for project in Project.select(query, clauseTables=clauseTables):
            if project not in results:
                results.append(project)
        return results

    def search(self, text=None, soyuz=None,
                     rosetta=None, malone=None,
                     bazaar=None,
                     search_products=True,
                     show_inactive=False):
        """Search through the Registry database for projects that match the
        query terms. text is a piece of text in the title / summary /
        description fields of project (and possibly product). soyuz,
        bounties, bazaar, malone etc are hints as to whether the search
        should be limited to projects that are active in those Launchpad
        applications.
        """
        clauseTables = set()
        clauseTables.add('Project')
        queries = []
        if rosetta:
            clauseTables.add('Product')
            clauseTables.add('POTemplate')
            queries.append('POTemplate.product=Product.id')
        if malone:
            clauseTables.add('Product')
            clauseTables.add('BugTask')
            queries.append('BugTask.product=Product.id')
        if bazaar:
            clauseTables.add('Product')
            clauseTables.add('ProductSeries')
            queries.append('(ProductSeries.import_branch IS NOT NULL OR '
                           'ProductSeries.user_branch IS NOT NULL)')
            queries.append('ProductSeries.product=Product.id')

        if text:
            if search_products:
                clauseTables.add('Product')
                queries.append("Product.fti @@ ftq(%s)" % sqlvalues(text))
            else:
                queries.append("Project.fti @@ ftq(%s)" % sqlvalues(text))

        if 'Product' in clauseTables:
            queries.append('Product.project=Project.id')

        if not show_inactive:
            queries.append('Project.active IS TRUE')
            if 'Product' in clauseTables:
                queries.append('Product.active IS TRUE')

        query = " AND ".join(queries)
        return Project.select(query, distinct=True, clauseTables=clauseTables)

