# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to Product."""

__metaclass__ = type
__all__ = ['Product', 'ProductSet']


from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound, IntCol, AND)
from zope.interface import implements
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.database.branchvisibilitypolicy import (
    BranchVisibilityPolicyMixin)
from canonical.launchpad.database.bug import (
    BugSet, get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bugtask import BugTask, BugTaskSet
from canonical.launchpad.database.cal import Calendar
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.karma import KarmaContextMixin
from canonical.launchpad.database.faq import FAQ, FAQSearch
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.productbounty import ProductBounty
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.question import (
    QuestionTargetSearch, QuestionTargetMixin)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.sprint import HasSprintsMixin
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    DEFAULT_BRANCH_STATUS_IN_LISTING, BranchType, ICalendarOwner, IFAQTarget,
    IHasIcon, IHasLogo, IHasMugshot, ILaunchpadCelebrities,
    ILaunchpadStatisticSet, IPersonSet, IProduct, IProductSet,
    IQuestionTarget, NotFoundError, QUESTION_STATUS_DEFAULT_SEARCH)
from canonical.lp.dbschema import (
    License, TranslationPermission, SpecificationSort, SpecificationFilter,
    SpecificationDefinitionStatus, SpecificationImplementationStatus)


class Product(SQLBase, BugTargetBase, HasSpecificationsMixin, HasSprintsMixin,
              KarmaContextMixin, BranchVisibilityPolicyMixin,
              QuestionTargetMixin, HasTranslationImportsMixin):
    """A Product."""

    implements(IProduct, ICalendarOwner, IFAQTarget, IQuestionTarget,
               IHasLogo, IHasMugshot, IHasIcon)

    _table = 'Product'

    project = ForeignKey(
        foreignKey="Project", dbName="project", notNull=False, default=None)
    owner = ForeignKey(
        foreignKey="Person", dbName="owner", notNull=True)
    bugcontact = ForeignKey(
        dbName='bugcontact', foreignKey='Person', notNull=False, default=None)
    security_contact = ForeignKey(
        dbName='security_contact', foreignKey='Person', notNull=False,
        default=None)
    driver = ForeignKey(
        foreignKey="Person", dbName="driver", notNull=False, default=None)
    name = StringCol(
        dbName='name', notNull=True, alternateID=True, unique=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    summary = StringCol(dbName='summary', notNull=True)
    description = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
    screenshotsurl = StringCol(
        dbName='screenshotsurl', notNull=False, default=None)
    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)
    programminglang = StringCol(
        dbName='programminglang', notNull=False, default=None)
    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)
    translationgroup = ForeignKey(
        dbName='translationgroup', foreignKey='TranslationGroup',
        notNull=False, default=None)
    translationpermission = EnumCol(
        dbName='translationpermission', notNull=True,
        schema=TranslationPermission, default=TranslationPermission.OPEN)
    bugtracker = ForeignKey(
        foreignKey="BugTracker", dbName="bugtracker", notNull=False,
        default=None)
    official_answers = BoolCol(
        dbName='official_answers', notNull=True, default=False)
    official_malone = BoolCol(
        dbName='official_malone', notNull=True, default=False)
    official_rosetta = BoolCol(
        dbName='official_rosetta', notNull=True, default=False)
    active = BoolCol(dbName='active', notNull=True, default=True)
    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    private_bugs = BoolCol(
        dbName='private_bugs', notNull=True, default=False)
    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)
    freshmeatproject = StringCol(notNull=False, default=None)
    sourceforgeproject = StringCol(notNull=False, default=None)
    # While the interface defines this field as required, we need to
    # allow it to be NULL so we can create new product records before
    # the corresponding series records.
    development_focus = ForeignKey(
        foreignKey="ProductSeries", dbName="development_focus", notNull=False,
        default=None)

    calendar = ForeignKey(
        dbName='calendar', foreignKey='Calendar', default=None,
        forceDBName=True)

    license = EnumCol(
        dbName='license', notNull=False,
        schema=License, default=None)

    def _getBugTaskContextWhereClause(self):
        """See BugTargetBase."""
        return "BugTask.product = %d" % self.id

    def getExternalBugTracker(self):
        """See `IProduct`."""
        if self.official_malone:
            return None
        elif self.bugtracker is not None:
            return self.bugtracker
        elif self.project is not None:
            return self.project.bugtracker
        else:
            return None

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setProduct(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See `IBugTarget`."""
        return get_bug_tags("BugTask.product = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See `IBugTarget`."""
        return get_bug_tags_open_count(
            "BugTask.product = %s" % sqlvalues(self), user)

    def getOrCreateCalendar(self):
        if not self.calendar:
            self.calendar = Calendar(
                title='%s Product Calendar' % self.displayname,
                revision=0)
        return self.calendar

    branches = SQLMultipleJoin('Branch', joinColumn='product',
        orderBy='id')
    serieses = SQLMultipleJoin('ProductSeries', joinColumn='product',
        orderBy='name')

    @property
    def name_with_project(self):
        """See lib.canonical.launchpad.interfaces.IProduct"""
        if self.project and self.project.name != self.name:
            return self.project.name + ": " + self.name
        return self.name

    @property
    def releases(self):
        return ProductRelease.select(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == self.id),
            clauseTables=['ProductSeries'],
            orderBy=['version']
            )

    @property
    def drivers(self):
        """See `IProduct`."""
        drivers = set()
        drivers.add(self.driver)
        if self.project is not None:
            drivers.add(self.project.driver)
        drivers.discard(None)
        if len(drivers) == 0:
            if self.project is not None:
                drivers.add(self.project.owner)
            else:
                drivers.add(self.owner)
        return sorted(drivers, key=lambda driver: driver.browsername)

    bounties = SQLRelatedJoin(
        'Bounty', joinColumn='product', otherColumn='bounty',
        intermediateTable='ProductBounty')

    @property
    def all_milestones(self):
        """See `IProduct`."""
        return Milestone.selectBy(
            product=self, orderBy=['dateexpected', 'name'])

    @property
    def milestones(self):
        """See `IProduct`."""
        return Milestone.selectBy(
            product=self, visible=True, orderBy=['dateexpected', 'name'])

    @property
    def sourcepackages(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        clause = """ProductSeries.id=Packaging.productseries AND
                    ProductSeries.product = %s
                    """ % sqlvalues(self.id)
        clauseTables = ['ProductSeries']
        ret = Packaging.select(clause, clauseTables,
            prejoins=["sourcepackagename", "distroseries.distribution"])
        sps = [SourcePackage(sourcepackagename=r.sourcepackagename,
                             distroseries=r.distroseries) for r in ret]
        return sorted(sps, key=lambda x:
            (x.sourcepackagename.name, x.distroseries.name,
             x.distroseries.distribution.name))

    @property
    def distrosourcepackages(self):
        from canonical.launchpad.database.distributionsourcepackage \
            import DistributionSourcePackage
        clause = """ProductSeries.id=Packaging.productseries AND
                    ProductSeries.product = %s
                    """ % sqlvalues(self.id)
        clauseTables = ['ProductSeries']
        ret = Packaging.select(clause, clauseTables,
            prejoins=["sourcepackagename", "distroseries.distribution"])
        distros = set()
        dsps = []
        for packaging in ret:
            distro = packaging.distroseries.distribution
            if distro in distros:
                continue
            distros.add(distro)
            dsps.append(DistributionSourcePackage(
                sourcepackagename=packaging.sourcepackagename,
                distribution=distro))
        return sorted(dsps, key=lambda x:
            (x.sourcepackagename.name, x.distribution.name))

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.displayname

    @property
    def bugtargetname(self):
        """See `IBugTarget`."""
        return self.name

    def getLatestBranches(self, quantity=5, visible_by_user=None):
        """See `IProduct`."""
        return shortlist(
            BranchSet().getLatestBranchesForProduct(
                self, quantity, visible_by_user))

    def getPackage(self, distroseries):
        """See `IProduct`."""
        if isinstance(distroseries, Distribution):
            distroseries = distroseries.currentrelease
        for pkg in self.sourcepackages:
            if pkg.distroseries == distroseries:
                return pkg
        else:
            raise NotFoundError(distroseries)

    def getMilestone(self, name):
        """See `IProduct`."""
        return Milestone.selectOne("""
            product = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def createBug(self, bug_params):
        """See `IBugTarget`."""
        bug_params.setBugTarget(product=self)
        return BugSet().createBug(bug_params)

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.product = %s' % sqlvalues(self)

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
            product=self,
            search_text=search_text, status=status,
            language=language, sort=sort, owner=owner,
            needs_attention_from=needs_attention_from,
            unsupported_target=unsupported_target).getResults()

    def getTargetTypes(self):
        """See `QuestionTargetMixin`.

        Defines product as self.
        """
        return {'product': self}

    def newFAQ(self, owner, title, content, keywords=None, date_created=None):
        """See `IFAQTarget`."""
        return FAQ.new(
            owner=owner, title=title, content=content, keywords=keywords,
            date_created=date_created, product=self)

    def findSimilarFAQs(self, summary):
        """See `IFAQTarget`."""
        return FAQ.findSimilar(summary, product=self)

    def getFAQ(self, id):
        """See `IFAQCollection`."""
        return FAQ.getForTarget(id, self)

    def searchFAQs(self, search_text=None, owner=None, sort=None):
        """See `IFAQCollection`."""
        return FAQSearch(
            search_text=search_text, owner=owner, sort=sort,
            product=self).getResults()

    @property
    def translatable_packages(self):
        """See `IProduct`."""
        packages = set(package for package in self.sourcepackages
                       if len(package.currentpotemplates) > 0)
        # Sort packages by distroseries.name and package.name
        return sorted(packages, key=lambda p: (p.distroseries.name, p.name))

    @property
    def translatable_series(self):
        """See `IProduct`."""
        series = ProductSeries.select('''
            POTemplate.productseries = ProductSeries.id AND
            ProductSeries.product = %d
            ''' % self.id,
            clauseTables=['POTemplate'],
            orderBy='datecreated', distinct=True)
        return list(series)

    @property
    def primary_translatable(self):
        """See `IProduct`."""
        packages = self.translatable_packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        targetseries = ubuntu.currentseries
        series = self.translatable_series

        # First, go with development focus branch
        if series and self.development_focus in series:
            return self.development_focus
        # Next, go with the latest product series that has templates:
        if series:
            return series[-1]
        # Otherwise, look for an Ubuntu package in the current distroseries:
        for package in packages:
            if package.distroseries == targetseries:
                return package
        # now let's make do with any ubuntu package
        for package in packages:
            if package.distribution == ubuntu:
                return package
        # or just any package
        if len(packages) > 0:
            return packages[0]
        # capitulate
        return None

    @property
    def mentoring_offers(self):
        """See `IProduct`"""
        via_specs = MentoringOffer.select("""
            Specification.product = %s AND
            Specification.id = MentoringOffer.specification
            """ % sqlvalues(self.id) + """ AND NOT
            (""" + Specification.completeness_clause +")",
            clauseTables=['Specification'],
            distinct=True)
        via_bugs = MentoringOffer.select("""
            BugTask.product = %s AND
            BugTask.bug = MentoringOffer.bug AND
            BugTask.bug = Bug.id AND
            Bug.private IS FALSE
            """ % sqlvalues(self.id) + """ AND NOT (
            """ + BugTask.completeness_clause + ")",
            clauseTables=['BugTask', 'Bug'],
            distinct=True)
        return via_specs.union(via_bugs, orderBy=['-date_created', '-id'])

    @property
    def translationgroups(self):
        tg = []
        if self.translationgroup:
            tg.append(self.translationgroup)
        if self.project:
            if self.project.translationgroup:
                if self.project.translationgroup not in tg:
                    tg.append(self.project.translationgroup)

    @property
    def aggregatetranslationpermission(self):
        perms = [self.translationpermission]
        if self.project:
            perms.append(self.project.translationpermission)
        # XXX Carlos Perello Marin 2005-06-02:
        # Reviewer please describe a better way to explicitly order
        # the enums. The spec describes the order, and the values make
        # it work, and there is space left for new values so we can
        # ensure a consistent sort order in future, but there should be
        # a better way.
        return max(perms)

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
            # which for a product is to show incomplete specs
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
        # products, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - informational.
        #
        base = 'Specification.product = %s' % self.id
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
        return Specification.selectOneBy(product=self, name=name)

    def getSeries(self, name):
        """See `IProduct`."""
        return ProductSeries.selectOneBy(product=self, name=name)

    def newSeries(self, owner, name, summary, branch=None):
        return ProductSeries(product=self, owner=owner, name=name,
                             summary=summary, user_branch=branch)

    def getRelease(self, version):
        return ProductRelease.selectOne("""
            ProductRelease.productseries = ProductSeries.id AND
            ProductSeries.product = %s AND
            ProductRelease.version = %s
            """ % sqlvalues(self.id, version),
            clauseTables=['ProductSeries'])

    def packagedInDistros(self):
        distros = Distribution.select(
            "Packaging.productseries = ProductSeries.id AND "
            "ProductSeries.product = %s AND "
            "Packaging.distrorelease = DistroRelease.id AND "
            "DistroRelease.distribution = Distribution.id"
            "" % sqlvalues(self.id),
            clauseTables=['Packaging', 'ProductSeries', 'DistroRelease'],
            orderBy='name',
            distinct=True
            )
        return distros

    def ensureRelatedBounty(self, bounty):
        """See `IProduct`."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        ProductBounty(product=self, bounty=bounty)
        return None


class ProductSet:
    implements(IProductSet)

    def __init__(self):
        self.title = "Projects in Launchpad"

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        item = Product.selectOneBy(name=name, active=True)
        if item is None:
            raise NotFoundError(name)
        return item

    def __iter__(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return iter(self.all_active)

    @property
    def people(self):
        return getUtility(IPersonSet)

    def latest(self, quantity=5):
        return self.all_active[:quantity]

    @property
    def all_active(self):
        results = Product.selectBy(
            active=True, orderBy="-Product.datecreated")
        # The main product listings include owner, so we prejoin it in
        return results.prejoin(["owner"])

    def get(self, productid):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        try:
            return Product.get(productid)
        except SQLObjectNotFound:
            raise NotFoundError("Product with ID %s does not exist" %
                                str(productid))

    def getByName(self, name, default=None, ignore_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        if ignore_inactive:
            product = Product.selectOneBy(name=name, active=True)
        else:
            product = Product.selectOneBy(name=name)
        if product is None:
            return default
        return product

    def getProductsWithBranches(self, num_products=None):
        """See `IProductSet`."""
        results = Product.select('''
            Product.id in (
                select distinct(product) from Branch
                where lifecycle_status in %s)
            ''' % sqlvalues(DEFAULT_BRANCH_STATUS_IN_LISTING),
            orderBy='name')
        if num_products is not None:
            results = results.limit(num_products)
        return results

    def getProductsWithUserDevelopmentBranches(self):
        """See `IProductSet`."""
        return Product.select('''
            Product.development_focus = ProductSeries.id and
            ProductSeries.user_branch = Branch.id and
            Branch.branch_type in %s
            ''' % quote((BranchType.HOSTED, BranchType.MIRRORED)),
            orderBy='name', clauseTables=['ProductSeries', 'Branch'])

    def createProduct(self, owner, name, displayname, title, summary,
                      description=None, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None,
                      reviewed=False, mugshot=None, logo=None,
                      icon=None):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        product = Product(
            owner=owner, name=name, displayname=displayname,
            title=title, project=project, summary=summary,
            description=description, homepageurl=homepageurl,
            screenshotsurl=screenshotsurl, wikiurl=wikiurl,
            downloadurl=downloadurl, freshmeatproject=freshmeatproject,
            sourceforgeproject=sourceforgeproject,
            programminglang=programminglang, reviewed=reviewed,
            icon=icon, logo=logo, mugshot=mugshot)

        # Create a default trunk series and set it as the development focus
        trunk = product.newSeries(owner, 'trunk', 'The "trunk" series '
            'represents the primary line of development rather than '
            'a stable release branch. This is sometimes also called MAIN '
            'or HEAD.')
        product.development_focus = trunk

        return product

    def forReview(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product.select("reviewed IS FALSE")

    def search(self, text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None,
               show_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        # XXX: kiko 2006-03-22: The soyuz argument is unused.
        clauseTables = set()
        clauseTables.add('Product')
        queries = []
        if text:
            queries.append("Product.fti @@ ftq(%s) " % sqlvalues(text))
        if rosetta:
            clauseTables.add('POTemplate')
            clauseTables.add('ProductRelease')
            clauseTables.add('ProductSeries')
            queries.append("POTemplate.productrelease=ProductRelease.id")
            queries.append("ProductRelease.productseries=ProductSeries.id")
            queries.append("ProductSeries.product=product.id")
        if malone:
            clauseTables.add('BugTask')
            queries.append('BugTask.product=Product.id')
        if bazaar:
            clauseTables.add('ProductSeries')
            queries.append('(ProductSeries.import_branch IS NOT NULL OR '
                           'ProductSeries.user_branch IS NOT NULL)')
        if 'ProductSeries' in clauseTables:
            queries.append('ProductSeries.product=Product.id')
        if not show_inactive:
            queries.append('Product.active IS TRUE')
        query = " AND ".join(queries)
        return Product.select(query, distinct=True,
                              prejoins=["owner"],
                              clauseTables=clauseTables)

    def getTranslatables(self):
        """See `IProductSet`"""
        upstream = Product.select('''
            Product.id = ProductSeries.product AND
            POTemplate.productseries = ProductSeries.id AND
            Product.official_rosetta
            ''',
            clauseTables=['ProductSeries', 'POTemplate'],
            orderBy='Product.title',
            distinct=True)
        return upstream

    def featuredTranslatables(self, maximumproducts=8):
        """See `IProductSet`"""
        randomresults = Product.select('''id IN
            (SELECT Product.id FROM Product, ProductSeries, POTemplate
               WHERE Product.id = ProductSeries.product AND
                     POTemplate.productseries = ProductSeries.id AND
                     Product.official_rosetta
               ORDER BY random())
            ''',
            distinct=True)

        results = list(randomresults[:maximumproducts])
        results.sort(lambda a, b: cmp(a.title, b.title))
        return results

    @cachedproperty
    def stats(self):
        return getUtility(ILaunchpadStatisticSet)

    def count_all(self):
        return self.stats.value('active_products')

    def count_translatable(self):
        return self.stats.value('products_with_translations')

    def count_reviewed(self):
        return self.stats.value('reviewed_products')

    def count_buggy(self):
        return self.stats.value('projects_with_bugs')

    def count_featureful(self):
        return self.stats.value('products_with_blueprints')

    def count_answered(self):
        return self.stats.value('products_with_questions')

    def count_codified(self):
        return self.stats.value('products_with_branches')


