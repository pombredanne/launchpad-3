# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Components related to IBugTarget."""

__metaclass__ = type
__all__ = [
    'BugTargetBase',
    'HasBugsBase',
    'HasBugHeatMixin',
    'OfficialBugTag',
    'OfficialBugTagTargetMixin',
    ]

from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import (
    cursor,
    sqlvalues,
    )
from canonical.launchpad.interfaces.lpstorm import (
    IMasterObject,
    IMasterStore,
    )
from canonical.launchpad.searchbuilder import (
    any,
    not_equals,
    NULL,
    )
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    ILaunchBag,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.bugs.interfaces.bugtarget import IOfficialBugTag
from lp.bugs.interfaces.bugtask import (
    BugTagsSearchCombinator,
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    BugTaskStatusSearch,
    RESOLVED_BUGTASK_STATUSES,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.bugs.interfaces.bugtaskfilter import simple_weight_calculator
from lp.bugs.model.bugtask import (
    BugTaskSet,
    get_bug_privacy_filter,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.sourcepackage import ISourcePackage


class HasBugsBase:
    """Standard functionality for IHasBugs.

    All `IHasBugs` implementations should inherit from this class
    or from `BugTargetBase`.
    """

    def searchTasks(self, search_params, user=None,
                    order_by=None, search_text=None,
                    status=None,
                    importance=None,
                    assignee=None, bug_reporter=None, bug_supervisor=None,
                    bug_commenter=None, bug_subscriber=None, owner=None,
                    structural_subscriber=None,
                    affected_user=None, affects_me=False,
                    has_patch=None, has_cve=None, distribution=None,
                    tags=None, tags_combinator=BugTagsSearchCombinator.ALL,
                    omit_duplicates=True, omit_targeted=None,
                    status_upstream=None, milestone_assignment=None,
                    milestone=None, component=None, nominated_for=None,
                    sourcepackagename=None, has_no_package=None,
                    hardware_bus=None, hardware_vendor_id=None,
                    hardware_product_id=None, hardware_driver_name=None,
                    hardware_driver_package_name=None,
                    hardware_owner_is_bug_reporter=None,
                    hardware_owner_is_affected_by_bug=False,
                    hardware_owner_is_subscribed_to_bug=False,
                    hardware_is_linked_to_bug=False, linked_branches=None,
                    linked_blueprints=None, modified_since=None,
                    created_since=None, prejoins=[]):
        """See `IHasBugs`."""
        if status is None:
            # If no statuses are supplied, default to the
            # list of all unreolved statuses.
            status = list(UNRESOLVED_BUGTASK_STATUSES)

        if order_by is None:
            # If no order_by value is supplied, default to importance.
            order_by = ['-importance']

        if search_params is None:
            kwargs = dict(locals())
            del kwargs['self']
            del kwargs['user']
            del kwargs['search_params']
            del kwargs['prejoins']
            search_params = BugTaskSearchParams.fromSearchForm(user, **kwargs)
        self._customizeSearchParams(search_params)
        return BugTaskSet().search(search_params, prejoins=prejoins)

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for a specific target."""
        raise NotImplementedError(self._customizeSearchParams)

    def getBugSummaryContextWhereClause(self):
        """Return a storm clause to filter bugsummaries on this context.

        :return: Either a storm clause to filter bugsummaries, or False if
            there cannot be any matching bug summaries.
        """
        raise NotImplementedError(self.getBugSummaryContextWhereClause)

    @property
    def closed_bugtasks(self):
        """See `IHasBugs`."""
        closed_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*RESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(closed_tasks_query)

    @property
    def open_bugtasks(self):
        """See `IHasBugs`."""
        return self.searchTasks(BugTaskSet().open_bugtask_search)

    @property
    def new_bugtasks(self):
        """See `IHasBugs`."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.NEW,
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def high_bugtasks(self):
        """See `IHasBugs`."""
        high_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            importance=BugTaskImportance.HIGH,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(high_tasks_query)

    @property
    def critical_bugtasks(self):
        """See `IHasBugs`."""
        critical_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            importance=BugTaskImportance.CRITICAL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(critical_tasks_query)

    @property
    def inprogress_bugtasks(self):
        """See `IHasBugs`."""
        inprogress_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=BugTaskStatus.INPROGRESS,
            omit_dupes=True)

        return self.searchTasks(inprogress_tasks_query)

    @property
    def unassigned_bugtasks(self):
        """See `IHasBugs`."""
        unassigned_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, assignee=NULL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES), omit_dupes=True)

        return self.searchTasks(unassigned_tasks_query)

    @property
    def all_bugtasks(self):
        """See `IHasBugs`."""
        all_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=not_equals(BugTaskStatus.UNKNOWN))

        return self.searchTasks(all_tasks_query)

    @property
    def has_bugtasks(self):
        """See `IHasBugs`."""
        return not self.all_bugtasks.is_empty()

    def getBugTaskWeightFunction(self):
        """Default weight function is the simple one."""
        return simple_weight_calculator


class BugTargetBase(HasBugsBase):
    """Standard functionality for IBugTargets.

    All IBugTargets should inherit from this class.
    """

    # The default implementation of the property, used for
    # IDistribution, IDistroSeries, IProjectGroup.
    enable_bugfiling_duplicate_search = True

    def getUsedBugTagsWithOpenCounts(self, user, tag_limit=0,
                                     include_tags=None):
        """See IBugTarget."""
        from lp.bugs.model.bug import get_bug_tags_open_count
        return get_bug_tags_open_count(
            self.getBugSummaryContextWhereClause(),
            user, tag_limit=tag_limit, include_tags=include_tags)


class HasBugHeatMixin:
    """Standard functionality for objects implementing IHasBugHeat."""

    def setMaxBugHeat(self, heat):
        """See `IHasBugHeat`."""
        if (IDistribution.providedBy(self)
            or IProduct.providedBy(self)
            or IProjectGroup.providedBy(self)
            or IDistributionSourcePackage.providedBy(self)):
            # Only objects that don't delegate have a setter.
            self.max_bug_heat = heat
        else:
            raise NotImplementedError

    def recalculateBugHeatCache(self):
        """See `IHasBugHeat`.

        DistributionSourcePackage overrides this method.
        """
        if IProductSeries.providedBy(self):
            return self.product.recalculateBugHeatCache()
        if IDistroSeries.providedBy(self):
            return self.distribution.recalculateBugHeatCache()
        if ISourcePackage.providedBy(self):
            # Should only happen for nominations, so we can safely skip
            # recalculating max_heat.
            return

        # XXX: deryck The queries here are a source of pain and have
        # been changed a couple times looking for the best
        # performaning version.  Use caution and have EXPLAIN ANALYZE
        # data ready when changing these.
        if IDistribution.providedBy(self):
            sql = ["""SELECT Bug.heat
                      FROM Bug, Bugtask
                      WHERE Bugtask.bug = Bug.id
                      AND Bugtask.distribution = %s
                      ORDER BY Bug.heat DESC LIMIT 1""" % sqlvalues(self),
                   """SELECT Bug.heat
                      FROM Bug, Bugtask, DistroSeries
                      WHERE Bugtask.bug = Bug.id
                      AND Bugtask.distroseries = DistroSeries.id
                      AND Bugtask.distroseries IS NOT NULL
                      AND DistroSeries.distribution = %s
                      ORDER BY Bug.heat DESC LIMIT 1""" % sqlvalues(self)]
        elif IProduct.providedBy(self):
            sql = ["""SELECT Bug.heat
                      FROM Bug, Bugtask
                      WHERE Bugtask.bug = Bug.id
                      AND Bugtask.product = %s
                      ORDER BY Bug.heat DESC LIMIT 1""" % sqlvalues(self),
                   """SELECT Bug.heat
                      FROM Bug, Bugtask, ProductSeries
                      WHERE Bugtask.bug = Bug.id
                      AND Bugtask.productseries IS NOT NULL
                      AND Bugtask.productseries = ProductSeries.id
                      AND ProductSeries.product = %s
                      ORDER BY Bug.heat DESC LIMIT 1""" % sqlvalues(self)]
        elif IProjectGroup.providedBy(self):
            sql = ["""SELECT Bug.heat
                      FROM Bug, Bugtask, Product
                      WHERE Bugtask.bug = Bug.id
                      AND Bugtask.product = Product.id
                      AND Product.project IS NOT NULL
                      AND Product.project =  %s
                      ORDER BY Bug.heat DESC LIMIT 1""" % sqlvalues(self)]
        else:
            raise NotImplementedError

        results = [0]
        for query in sql:
            cur = cursor()
            cur.execute(query)
            record = cur.fetchone()
            if record is not None:
                results.append(record[0])
            cur.close()
        self.setMaxBugHeat(max(results))

        # If the product is part of a project group we calculate the maximum
        # heat for the project group too.
        if IProduct.providedBy(self) and self.project is not None:
            self.project.recalculateBugHeatCache()


class OfficialBugTagTargetMixin:
    """See `IOfficialBugTagTarget`.

    This class is intended to be used as a mixin for the classes
    Distribution, Product and ProjectGroup, which can define official
    bug tags.

    Using this call in ProjectGroup requires a fix of bug 341203, see
    below, class OfficialBugTag.

    See also `Bug.official_bug_tags` which calculates this efficiently for
    a single bug.
    """

    def _getOfficialTagClause(self):
        if IDistribution.providedBy(self):
            return (OfficialBugTag.distribution == self)
        elif IProduct.providedBy(self):
            return (OfficialBugTag.product == self)
        else:
            raise AssertionError(
                '%s is not a valid official bug target' % self)

    def _getOfficialTags(self):
        """Get the official bug tags as a sorted list of strings."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        target_clause = self._getOfficialTagClause()
        return list(store.find(
            OfficialBugTag.tag, target_clause).order_by(OfficialBugTag.tag))

    def _setOfficialTags(self, tags):
        """Set the official bug tags from a list of strings."""
        new_tags = set([tag.lower() for tag in tags])
        old_tags = set(self.official_bug_tags)
        added_tags = new_tags.difference(old_tags)
        removed_tags = old_tags.difference(new_tags)
        for removed_tag in removed_tags:
            self.removeOfficialBugTag(removed_tag)
        for added_tag in added_tags:
            self.addOfficialBugTag(added_tag)

    official_bug_tags = property(_getOfficialTags, _setOfficialTags)

    def _getTag(self, tag):
        """Return the OfficialBugTag record for the given tag, if it exists.

        If the tag is not defined for this target, None is returned.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        target_clause = self._getOfficialTagClause()
        return store.find(
            OfficialBugTag, OfficialBugTag.tag==tag, target_clause).one()

    def addOfficialBugTag(self, tag):
        """See `IOfficialBugTagTarget`."""
        # Tags must be unique per target; adding an existing tag
        # for a second time would lead to an exception.
        if self._getTag(tag) is None:
            new_tag = OfficialBugTag()
            new_tag.tag = tag
            new_tag.target = IMasterObject(self)
            IMasterStore(OfficialBugTag).add(new_tag)

    def removeOfficialBugTag(self, tag):
        """See `IOfficialBugTagTarget`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        tag = self._getTag(tag)
        if tag is not None:
            store.remove(tag)


class OfficialBugTag(Storm):
    """See `IOfficialBugTag`."""
    # XXX Abel Deuring, 2009-03-11: The SQL table OfficialBugTag has
    # a column "project", while a constraint requires that either "product"
    # or "distribution" must be non-null. Once this is changed, we
    # should add the column "project" here. Bug #341203.

    implements(IOfficialBugTag)

    __storm_table__ = 'OfficialBugTag'

    id = Int(primary=True)

    tag = Unicode(allow_none=False)
    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, 'Distribution.id')

    product_id = Int(name='product')
    product = Reference(product_id, 'Product.id')

    def target(self):
        """See `IOfficialBugTag`."""
        # A database constraint ensures that either distribution or
        # product is not None.
        if self.distribution is not None:
            return self.distribution
        else:
            return self.product

    def _settarget(self, target):
        """See `IOfficialBugTag`."""
        if IDistribution.providedBy(target):
            self.distribution = target
        elif IProduct.providedBy(target):
            self.product = target
        else:
            raise ValueError(
                'The target of an OfficialBugTag must be either an '
                'IDistribution instance or an IProduct instance.')

    target = property(target, _settarget, doc=target.__doc__)
