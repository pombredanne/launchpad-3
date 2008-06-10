# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'ProductSeries',
    'ProductSeriesSet',
    ]

import datetime
from sqlobject import (
    IntervalCol, ForeignKey, StringCol, SQLMultipleJoin, SQLObjectNotFound)
from warnings import warn
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, quote, sqlvalues)
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bug import (
    get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscriptionTargetMixin)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces import (
    IHasTranslationTemplates, ImportStatus, IProductSeries, IProductSeriesSet,
    IProductSeriesSourceAdmin, IStructuralSubscriptionTarget, NotFoundError,
    PackagingType, RevisionControlSystems, SpecificationDefinitionStatus,
    SpecificationFilter, SpecificationGoalStatus,
    SpecificationImplementationStatus, SpecificationSort)


class ProductSeries(SQLBase, BugTargetBase, HasSpecificationsMixin,
                    HasTranslationImportsMixin,
                    StructuralSubscriptionTargetMixin):
    """A series of product releases."""
    implements(
        IProductSeries, IProductSeriesSourceAdmin, IHasTranslationTemplates,
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
        validator=public_person_validator, notNull=True)
    driver = ForeignKey(
        dbName="driver", foreignKey="Person",
        validator=public_person_validator, notNull=False, default=None)
    import_branch = ForeignKey(foreignKey='Branch', dbName='import_branch',
                               default=None)
    user_branch = ForeignKey(foreignKey='Branch', dbName='user_branch',
                             default=None)
    importstatus = EnumCol(dbName='importstatus', notNull=False,
        schema=ImportStatus, default=None)
    rcstype = EnumCol(dbName='rcstype', enum=RevisionControlSystems,
        notNull=False, default=None)
    cvsroot = StringCol(default=None)
    cvsmodule = StringCol(default=None)
    cvsbranch = StringCol(default=None)
    # where are the tarballs released from this branch placed?
    cvstarfileurl = StringCol(default=None)
    svnrepository = StringCol(default=None)
    releasefileglob = StringCol(default=None)
    releaseverstyle = StringCol(default=None)
    # key dates on the road to import happiness
    dateautotested = UtcDateTimeCol(default=None)
    datestarted = UtcDateTimeCol(default=None)
    datefinished = UtcDateTimeCol(default=None)
    dateprocessapproved = UtcDateTimeCol(default=None)
    datesyncapproved = UtcDateTimeCol(default=None)
    # controlling the freshness of an import
    syncinterval = IntervalCol(default=None)
    datelastsynced = UtcDateTimeCol(default=None)
    datepublishedsync = UtcDateTimeCol(
        dbName='date_published_sync', default=None)

    @property
    def new_style_import(self):
        """See `IProductSeries`."""
        # XXX: MichaelHudson 2008-05-20, bug=232076: This property is
        # only necessary for the transition from the old to the new
        # code import system, and should be deleted after that process
        # is done.
        # Local import to avoid circularity issues.
        from canonical.launchpad.database.codeimport import (
            _ProductSeriesCodeImport)
        pair = _ProductSeriesCodeImport.selectOneBy(
            productseries=self)
        if pair is not None:
            return pair.codeimport
        else:
            return None

    releases = SQLMultipleJoin('ProductRelease', joinColumn='productseries',
                            orderBy=['-datereleased'])
    packagings = SQLMultipleJoin('Packaging', joinColumn='productseries',
                            orderBy=['-id'])

    @property
    def release_files(self):
        """See IProductSeries."""
        files = set()
        for release in self.releases:
            files = files.union(release.files)
        return files

    @property
    def displayname(self):
        return self.name

    @property
    def all_milestones(self):
        """See IProductSeries."""
        return Milestone.selectBy(
            productseries=self, orderBy=['-dateexpected', 'name'])

    @property
    def milestones(self):
        """See IProductSeries."""
        return Milestone.selectBy(
            productseries=self, visible=True,
            orderBy=['-dateexpected', 'name'])

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

    @property
    def series_branch(self):
        """See IProductSeries."""
        if self.user_branch is not None:
            return self.user_branch
        return self.import_branch

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
        from canonical.launchpad.database.sourcepackage import SourcePackage
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

    def searchTasks(self, search_params):
        """See IBugTarget."""
        search_params.setProductSeries(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return get_bug_tags("BugTask.productseries = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.productseries = %s" % sqlvalues(self), user)

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

    def certifyForSync(self):
        """Enable the sync for processing."""
        self.dateprocessapproved = UTC_NOW
        if self.rcstype == RevisionControlSystems.CVS:
            self.syncinterval = datetime.timedelta(hours=12)
        elif self.rcstype == RevisionControlSystems.SVN:
            self.syncinterval = datetime.timedelta(hours=6)
        else:
            raise AssertionError(
                'Unknown default sync interval for rcs type: %s'
                % self.rcstype.title)
        self.importstatus = ImportStatus.PROCESSING

    def markTestFailed(self):
        """See `IProductSeriesSourceAdmin`."""
        self.importstatus = ImportStatus.TESTFAILED
        self.import_branch = None
        self.dateautotested = None
        self.dateprocessapproved = None
        self.datesyncapproved = None
        self.datelastsynced = None
        self.syncinterval = None

    def markDontSync(self):
        """See `IProductSeriesSourceAdmin`."""
        self.importstatus = ImportStatus.DONTSYNC
        self.import_branch = None
        self.dateautotested = None
        self.dateprocessapproved = None
        self.datesyncapproved = None
        self.datelastsynced = None
        self.datestarted = None
        self.datefinished = None
        self.syncinterval = None

    def markStopped(self):
        """See `IProductSeriesSourceAdmin`."""
        self.importstatus = ImportStatus.STOPPED
        self.dateautotested = None
        self.dateprocessapproved = None
        self.datesyncapproved = None
        self.datelastsynced = None
        self.datestarted = None
        self.datefinished = None
        self.syncinterval = None

    def deleteImport(self):
        """See `IProductSeriesSourceAdmin`."""
        self.importstatus = None
        self.import_branch = None
        self.dateautotested = None
        self.dateprocessapproved = None
        self.datesyncapproved = None
        self.datelastsynced = None
        self.datepublishedsync = None
        self.syncinterval = None
        self.datestarted = None
        self.datefinished = None
        self.rcstype = None
        self.cvsroot = None
        self.cvsmodule = None
        self.cvsbranch = None
        self.cvstarfileurl = None
        self.svnrepository = None

    def syncCertified(self):
        """Return true or false indicating if the sync is enabled"""
        return self.dateprocessapproved is not None

    def autoSyncEnabled(self):
        """Is the sync automatically scheduling?"""
        return self.importstatus == ImportStatus.SYNCING

    def enableAutoSync(self):
        """Enable autosyncing."""
        self.datesyncapproved = UTC_NOW
        self.importstatus = ImportStatus.SYNCING

    def autoTestFailed(self):
        """Has the series source failed automatic testing by roomba?"""
        return self.importstatus == ImportStatus.TESTFAILED

    def newMilestone(self, name, dateexpected=None, description=None):
        """See IProductSeries."""
        return Milestone(
            name=name, dateexpected=dateexpected, description=description,
            product=self.product, productseries=self)

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

    def searchImports(self, text=None, importstatus=None):
        """See `IProductSeriesSet`."""
        query = self.composeQueryString(text, importstatus)
        return ProductSeries.select(
            query, orderBy=['product.name', 'productseries.name'],
            clauseTables=['Product'])

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

    def getByCVSDetails(self, cvsroot, cvsmodule, cvsbranch, default=None):
        """See IProductSeriesSet."""
        result = ProductSeries.selectOneBy(
            cvsroot=cvsroot, cvsmodule=cvsmodule, cvsbranch=cvsbranch)
        if result is None:
            return default
        return result

    def getBySVNDetails(self, svnrepository, default=None):
        """See IProductSeriesSet."""
        result = ProductSeries.selectOneBy(svnrepository=svnrepository)
        if result is None:
            return default
        return result

    def getSeriesForBranches(self, branches):
        """See `IProductSeriesSet`."""
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return []

        return ProductSeries.select("""
            ProductSeries.user_branch in %s OR
            ProductSeries.import_branch in %s
            """ % sqlvalues(branch_ids, branch_ids), orderBy=["name"])
