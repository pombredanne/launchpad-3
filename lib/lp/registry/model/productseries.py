# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'ProductSeries',
    'ProductSeriesSet',
    ]

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLObjectNotFound)
from storm.expr import In
from warnings import warn
from zope.component import getUtility
from zope.interface import implements
from storm.locals import And, Desc
from storm.store import Store

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, quote, sqlvalues)
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bug import (
    get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtask import BugTask
from lp.registry.model.milestone import (
    HasMilestonesMixin, Milestone)
from canonical.launchpad.database.packaging import Packaging
from lp.registry.interfaces.person import validate_public_person
from canonical.launchpad.database.potemplate import POTemplate
from lp.registry.model.productrelease import ProductRelease
from lp.blueprints.model.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscriptionTargetMixin)
from canonical.launchpad.helpers import shortlist
from lp.registry.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces.packaging import PackagingType
from canonical.launchpad.interfaces.potemplate import IHasTranslationTemplates
from lp.blueprints.interfaces.specification import (
    SpecificationDefinitionStatus, SpecificationFilter,
    SpecificationGoalStatus, SpecificationImplementationStatus,
    SpecificationSort)
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.productseries import (
    IProductSeries, IProductSeriesSet)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)


class ProductSeries(SQLBase, BugTargetBase, HasMilestonesMixin,
                    HasSpecificationsMixin, HasTranslationImportsMixin,
                    StructuralSubscriptionTargetMixin):
    """A series of product releases."""
    implements(
        IProductSeries, IHasTranslationTemplates,
        IStructuralSubscriptionTarget)

    _table = 'ProductSeries'

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    status = EnumCol(
        notNull=True, schema=DistroSeriesStatus,
        default=DistroSeriesStatus.DEVELOPMENT)
    name = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(
        dbName="owner", foreignKey="Person",
        storm_validator=validate_public_person, notNull=True)
    driver = ForeignKey(
        dbName="driver", foreignKey="Person",
        storm_validator=validate_public_person, notNull=False, default=None)
    branch = ForeignKey(foreignKey='Branch', dbName='branch',
                             default=None)
    translations_autoimport_mode = EnumCol(
        dbName='translations_autoimport_mode',
        notNull=True,
        schema=TranslationsBranchImportMode,
        default=TranslationsBranchImportMode.NO_IMPORT)
    # where are the tarballs released from this branch placed?
    releasefileglob = StringCol(default=None)
    releaseverstyle = StringCol(default=None)

    packagings = SQLMultipleJoin('Packaging', joinColumn='productseries',
                            orderBy=['-id'])

    def _getMilestoneCondition(self):
        """See `HasMilestonesMixin`."""
        return (Milestone.productseries == self)

    @property
    def releases(self):
        """See `IProductSeries`."""
        store = Store.of(self)
        result = store.find(
            ProductRelease,
            And(Milestone.productseries == self,
                ProductRelease.milestone == Milestone.id))
        return result.order_by(Desc('datereleased'))

    @property
    def release_files(self):
        """See `IProductSeries`."""
        files = set()
        for release in self.releases:
            files = files.union(release.files)
        return files

    @property
    def displayname(self):
        return self.name

    @property
    def parent(self):
        """See IProductSeries."""
        return self.product

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return "%s %s" % (self.product.displayname, self.name)

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return "%s/%s" % (self.product.name, self.name)

    @property
    def drivers(self):
        """See IProductSeries."""
        drivers = set()
        drivers.add(self.driver)
        drivers = drivers.union(self.product.drivers)
        drivers.discard(None)
        return sorted(drivers, key=lambda x: x.browsername)

    @property
    def bug_supervisor(self):
        """See IProductSeries."""
        return self.product.bug_supervisor

    @property
    def security_contact(self):
        """See IProductSeries."""
        return self.product.security_contact

    def getPOTemplate(self, name):
        """See IProductSeries."""
        return POTemplate.selectOne(
            "productseries = %s AND name = %s" % sqlvalues(self.id, name))

    @property
    def title(self):
        return self.product.displayname + ' Series: ' + self.displayname

    def shortdesc(self):
        warn('ProductSeries.shortdesc should be ProductSeries.summary',
             DeprecationWarning)
        return self.summary
    shortdesc = property(shortdesc)

    @property
    def bug_reporting_guidelines(self):
        """See `IBugTarget`."""
        return self.product.bug_reporting_guidelines

    @property
    def sourcepackages(self):
        """See IProductSeries"""
        from lp.registry.model.sourcepackage import SourcePackage
        ret = Packaging.selectBy(productseries=self)
        ret = [SourcePackage(sourcepackagename=r.sourcepackagename,
                             distroseries=r.distroseries)
                    for r in ret]
        ret.sort(key=lambda a: a.distribution.name + a.distroseries.version
                 + a.sourcepackagename.name)
        return ret

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    @property
    def valid_specifications(self):
        return self.specifications(filter=[SpecificationFilter.VALID])

    @property
    def is_development_focus(self):
        """See `IProductSeries`."""
        return self == self.product.development_focus

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See IHasSpecifications.

        The rules for filtering are that there are three areas where you can
        apply a filter:

          - acceptance, which defaults to ACCEPTED if nothing is said,
          - completeness, which defaults to showing BOTH if nothing is said
          - informational, which defaults to showing BOTH if nothing is said

        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a productseries is to show everything accepted
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
            order = ['-priority', 'definition_status', 'name']
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
        # productseries, we need to be able to filter on the basis of:
        #
        #  - completeness. by default, only incomplete specs shown
        #  - goal status. by default, only accepted specs shown
        #  - informational.
        #
        base = 'Specification.productseries = %s' % self.id
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

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            query += (
                ' AND Specification.definition_status NOT IN ( %s, %s ) '
                % sqlvalues(SpecificationDefinitionStatus.OBSOLETE,
                            SpecificationDefinitionStatus.SUPERSEDED))

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        results = Specification.select(query, orderBy=order, limit=quantity)
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this product series."""
        search_params.setProductSeries(self)

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.product.official_bug_tags

    def getUsedBugTags(self):
        """See IBugTarget."""
        return get_bug_tags("BugTask.productseries = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(BugTask.productseries == self, user)

    def createBug(self, bug_params):
        """See IBugTarget."""
        raise NotImplementedError('Cannot file a bug against a productseries')

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.productseries = %s' % sqlvalues(self)

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.product.getSpecification(name)

    def getRelease(self, version):
        for release in self.releases:
            if release.version == version:
                return release
        return None

    def getPackage(self, distroseries):
        """See IProductSeries."""
        for pkg in self.sourcepackages:
            if pkg.distroseries == distroseries:
                return pkg
        # XXX sabdfl 2005-06-23: This needs to search through the ancestry of
        # the distroseries to try to find a relevant packaging record
        raise NotFoundError(distroseries)

    def setPackaging(self, distroseries, sourcepackagename, owner):
        """See IProductSeries."""
        for pkg in self.packagings:
            if pkg.distroseries == distroseries:
                # we have found a matching Packaging record
                if pkg.sourcepackagename == sourcepackagename:
                    # and it has the same source package name
                    return pkg
                # ok, we need to update this pkging record
                pkg.sourcepackagename = sourcepackagename
                pkg.owner = owner
                pkg.datecreated = UTC_NOW
                pkg.sync()  # convert UTC_NOW to actual datetime
                return pkg

        # ok, we didn't find a packaging record that matches, let's go ahead
        # and create one
        pkg = Packaging(distroseries=distroseries,
            sourcepackagename=sourcepackagename, productseries=self,
            packaging=PackagingType.PRIME,
            owner=owner)
        pkg.sync()  # convert UTC_NOW to actual datetime
        return pkg

    def getPackagingInDistribution(self, distribution):
        """See IProductSeries."""
        history = []
        for pkging in self.packagings:
            if pkging.distroseries.distribution == distribution:
                history.append(pkging)
        return history

    def newMilestone(self, name, dateexpected=None, summary=None,
                     code_name=None):
        """See IProductSeries."""
        return Milestone(
            name=name, dateexpected=dateexpected, summary=summary,
            product=self.product, productseries=self, code_name=code_name)

    def getTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.selectBy(productseries=self,
                                     orderBy=['-priority','name'])
        return shortlist(result, 300)

    def getCurrentTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            productseries = %s AND
            productseries = ProductSeries.id AND
            iscurrent IS TRUE AND
            ProductSeries.product = Product.id AND
            Product.official_rosetta IS TRUE
            ''' % sqlvalues(self),
            orderBy=['-priority','name'],
            clauseTables = ['ProductSeries', 'Product'])
        return shortlist(result, 300)

    def getObsoleteTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            productseries = %s AND
            productseries = ProductSeries.id AND
            ProductSeries.product = Product.id AND
            (iscurrent IS FALSE OR Product.official_rosetta IS FALSE)
            ''' % sqlvalues(self),
            orderBy=['-priority','name'],
            clauseTables = ['ProductSeries', 'Product'])
        return shortlist(result, 300)

    def getTimeline(self, include_inactive=False):
        landmarks = []
        for milestone in self.all_milestones:
            if milestone.product_release is None:
                # Skip inactive milestones, but include releases,
                # even if include_inactive is False.
                if not include_inactive and not milestone.active:
                    continue
                node_type = 'milestone'
            else:
                node_type = 'release'
            entry = dict(
                name=milestone.name,
                code_name=milestone.code_name,
                type=node_type)
            landmarks.append(entry)
        return dict(
            name=self.name,
            is_development_focus=self.is_development_focus,
            landmarks=landmarks)


class ProductSeriesSet:
    """See IProductSeriesSet."""

    implements(IProductSeriesSet)

    def __getitem__(self, series_id):
        """See IProductSeriesSet."""
        series = self.get(series_id)
        if series is None:
            raise NotFoundError(series_id)
        return series

    def get(self, series_id, default=None):
        """See IProductSeriesSet."""
        try:
            return ProductSeries.get(series_id)
        except SQLObjectNotFound:
            return default

    def composeQueryString(self, text=None, importstatus=None):
        """Build SQL "where" clause for `ProductSeries` search.

        :param text: Text to search for in the product and project titles and
            descriptions.
        :param importstatus: If specified, limit the list to series which have
            the given import status; if not specified or None, limit to series
            with non-NULL import status.
        """
        conditions = ["ProductSeries.product = Product.id"]
        if text == u'':
            text = None

        # First filter on text, if supplied.
        if text is not None:
            conditions.append("""
                ((Project.fti @@ ftq(%s) AND Product.project IS NOT NULL) OR
                Product.fti @@ ftq(%s))""" % (quote(text), quote(text)))

        # Exclude deactivated products.
        conditions.append('Product.active IS TRUE')

        # Exclude deactivated projects, too.
        conditions.append(
            "((Product.project = Project.id AND Project.active) OR"
            " Product.project IS NULL)")

        # Now just add the filter on import status.
        if importstatus is None:
            conditions.append('ProductSeries.importstatus IS NOT NULL')
        else:
            conditions.append('ProductSeries.importstatus = %s'
                              % sqlvalues(importstatus))

        # And build the query.
        query = " AND ".join(conditions)
        return """productseries.id IN
            (SELECT productseries.id FROM productseries, product, project
             WHERE %s) AND productseries.product = product.id""" % query

    def getSeriesForBranches(self, branches):
        """See `IProductSeriesSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        branch_ids = [branch.id for branch in branches]
        return store.find(
            ProductSeries,
            In(ProductSeries.branchID, branch_ids)).order_by(
            ProductSeries.name)
