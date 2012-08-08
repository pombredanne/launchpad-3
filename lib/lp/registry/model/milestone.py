# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212
"""Milestone model classes."""

__metaclass__ = type
__all__ = [
    'HasMilestonesMixin',
    'Milestone',
    'MilestoneData',
    'MilestoneSet',
    'ProjectMilestone',
    'milestone_sort_key',
    ]

import datetime
import httplib

from lazr.restful.declarations import error_status
from sqlobject import (
    AND,
    BoolCol,
    DateCol,
    ForeignKey,
    StringCol,
    )
from storm.expr import (
    And,
    Desc,
    Join,
    LeftJoin,
    Or,
    )
from storm.locals import Store
from storm.zope import IResultSet
from zope.component import getUtility
from zope.interface import implements

from lp.app.errors import NotFoundError
from lp.blueprints.model.specification import Specification
from lp.blueprints.model.specificationworkitem import SpecificationWorkItem
from lp.bugs.interfaces.bugsummary import IBugSummaryDimension
from lp.bugs.interfaces.bugtarget import IHasBugs
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
from lp.bugs.model.bugtarget import HasBugsBase
from lp.bugs.model.bugtask import BugTaskSet
from lp.bugs.model.structuralsubscription import (
    StructuralSubscriptionTargetMixin,
    )
from lp.registry.interfaces.milestone import (
    IHasMilestones,
    IMilestone,
    IMilestoneData,
    IMilestoneSet,
    IProjectGroupMilestone,
    )
from lp.registry.model.productrelease import ProductRelease
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.lpstorm import IStore
from lp.services.database.sqlbase import SQLBase
from lp.services.webapp.sorting import expand_numbers


FUTURE_NONE = datetime.date(datetime.MAXYEAR, 1, 1)


def milestone_sort_key(milestone):
    """Enable sorting by the Milestone dateexpected and name."""
    if milestone.dateexpected is None:
        # A datetime.datetime object cannot be compared with None.
        # Milestones with dateexpected=None are sorted as being
        # way in the future.
        date = FUTURE_NONE
    elif isinstance(milestone.dateexpected, datetime.datetime):
        # XXX: EdwinGrubbs 2009-02-06 bug=326384:
        # The Milestone.dateexpected should be changed into a date column,
        # since the class defines the field as a DateCol, so that a list
        # of milestones can't have some dateexpected attributes that are
        # datetimes and others that are dates, which can't be compared.
        date = milestone.dateexpected.date()
    else:
        date = milestone.dateexpected
    return (date, expand_numbers(milestone.name))


class HasMilestonesMixin:
    implements(IHasMilestones)

    _milestone_order = (
        'milestone_sort_key(Milestone.dateexpected, Milestone.name) DESC')

    def _getMilestoneCondition(self):
        """Provides condition for milestones and all_milestones properties.

        Subclasses need to override this method.

        :return: Storm ComparableExpr object.
        """
        raise NotImplementedError(
            "Unexpected class for mixin: %r" % self)

    @property
    def has_milestones(self):
        return not self.all_milestones.is_empty()

    @property
    def all_milestones(self):
        """See `IHasMilestones`."""
        store = Store.of(self)
        result = store.find(Milestone, self._getMilestoneCondition())
        return result.order_by(self._milestone_order)

    def _get_milestones(self):
        """See `IHasMilestones`."""
        store = Store.of(self)
        result = store.find(Milestone,
                            And(self._getMilestoneCondition(),
                                Milestone.active == True))
        return result.order_by(self._milestone_order)

    milestones = property(_get_milestones)


@error_status(httplib.BAD_REQUEST)
class MultipleProductReleases(Exception):
    """Raised when a second ProductRelease is created for a milestone."""

    def __init__(self, msg='A milestone can only have one ProductRelease.'):
        super(MultipleProductReleases, self).__init__(msg)


class MilestoneData:
    implements(IMilestoneData)

    @property
    def displayname(self):
        """See IMilestone."""
        return "%s %s" % (self.target.displayname, self.name)

    @property
    def title(self):
        raise NotImplementedError

    @property
    def specifications(self):
        raise NotImplementedError

    def bugtasks(self, user):
        """The list of non-conjoined bugtasks targeted to this milestone."""
        # Put the results in a list so that iterating over it multiple
        # times in this method does not make multiple queries.
        non_conjoined_slaves = list(
            getUtility(IBugTaskSet).getPrecachedNonConjoinedBugTasks(
                user, self))
        return non_conjoined_slaves


class Milestone(SQLBase, MilestoneData, StructuralSubscriptionTargetMixin,
                HasBugsBase):
    implements(IHasBugs, IMilestone, IBugSummaryDimension)

    active = BoolCol(notNull=True, default=True)

    # XXX: EdwinGrubbs 2009-02-06 bug=326384:
    # The Milestone.dateexpected should be changed into a date column,
    # since the class defines the field as a DateCol, so that a list of
    # milestones can't have some dateexpected attributes that are
    # datetimes and others that are dates, which can't be compared.
    dateexpected = DateCol(notNull=False, default=None)

    # XXX: Guilherme Salgado 2007-03-27 bug=40978:
    # Milestones should be associated with productseries/distroseries
    # so these columns are not needed.
    product = ForeignKey(dbName='product',
        foreignKey='Product', default=None)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', default=None)

    productseries = ForeignKey(dbName='productseries',
        foreignKey='ProductSeries', default=None)
    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', default=None)
    name = StringCol(notNull=True)
    summary = StringCol(notNull=False, default=None)
    code_name = StringCol(dbName='codename', notNull=False, default=None)

    @property
    def specifications(self):
        from lp.registry.model.person import Person
        store = Store.of(self)
        origin = [
            Specification,
            LeftJoin(
                SpecificationWorkItem,
                SpecificationWorkItem.specification_id == Specification.id),
            LeftJoin(Person, Specification.assigneeID == Person.id),
            ]

        results = store.using(*origin).find(
            (Specification, Person),
            Or(Specification.milestoneID == self.id,
               SpecificationWorkItem.milestone_id == self.id),
            Or(SpecificationWorkItem.deleted == None,
               SpecificationWorkItem.deleted == False))
        results.config(distinct=True)
        ordered_results = results.order_by(Desc(Specification.priority),
                                           Specification.definition_status,
                                           Specification.implementation_status,
                                           Specification.title)
        mapper = lambda row: row[0]
        return DecoratedResultSet(ordered_results, mapper)

    @property
    def target(self):
        """See IMilestone."""
        if self.product:
            return self.product
        elif self.distribution:
            return self.distribution

    @property
    def product_release(self):
        store = Store.of(self)
        result = store.find(ProductRelease,
                            ProductRelease.milestone == self.id)
        releases = list(result)
        if len(releases) == 0:
            return None
        else:
            return releases[0]

    @property
    def series_target(self):
        """See IMilestone."""
        if self.productseries:
            return self.productseries
        elif self.distroseries:
            return self.distroseries

    @property
    def title(self):
        """See IMilestone."""
        if not self.code_name:
            # XXX sinzui 2009-07-16 bug=400477: code_name may be None or ''.
            return self.displayname
        return ('%s "%s"') % (self.displayname, self.code_name)

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this milestone."""
        search_params.milestone = self

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.target.official_bug_tags

    def createProductRelease(self, owner, datereleased,
                             changelog=None, release_notes=None):
        """See `IMilestone`."""
        if self.product_release is not None:
            raise MultipleProductReleases()
        release = ProductRelease(
            owner=owner,
            changelog=changelog,
            release_notes=release_notes,
            datereleased=datereleased,
            milestone=self)
        return release

    def closeBugsAndBlueprints(self, user):
        """See `IMilestone`."""
        search = BugTaskSet().open_bugtask_search
        for bugtask in self.searchTasks(search):
            if bugtask.status == BugTaskStatus.FIXCOMMITTED:
                bugtask.bug.setStatus(
                    bugtask.target, BugTaskStatus.FIXRELEASED, user)

    def destroySelf(self):
        """See `IMilestone`."""
        params = BugTaskSearchParams(milestone=self, user=None)
        bugtasks = getUtility(IBugTaskSet).search(params)
        subscriptions = IResultSet(self.getSubscriptions())
        assert subscriptions.is_empty(), (
            "You cannot delete a milestone which has structural "
            "subscriptions.")
        assert bugtasks.count() == 0, (
            "You cannot delete a milestone which has bugtasks targeted "
            "to it.")
        assert self.specifications.count() == 0, (
            "You cannot delete a milestone which has specifications targeted "
            "to it.")
        assert self.product_release is None, (
            "You cannot delete a milestone which has a product release "
            "associated with it.")
        SQLBase.destroySelf(self)

    def getBugSummaryContextWhereClause(self):
        """See BugTargetBase."""
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        return BugSummary.milestone_id == self.id

    def setTags(self, tags, user):
        """See IMilestone."""
        # Circular reference prevention.
        from lp.registry.model.milestonetag import MilestoneTag
        store = Store.of(self)
        if tags:
            current_tags = set(self.getTags())
            new_tags = set(tags)
            if new_tags == current_tags:
                return
            # Removing deleted tags.
            to_remove = current_tags.difference(new_tags)
            if to_remove:
                store.find(
                    MilestoneTag, MilestoneTag.tag.is_in(to_remove)).remove()
            # Adding new tags.
            for tag in new_tags.difference(current_tags):
                store.add(MilestoneTag(self, tag, user))
        else:
            store.find(
                MilestoneTag, MilestoneTag.milestone_id == self.id).remove()

    def getTagsData(self):
        """See IMilestone."""
        # Prevent circular references.
        from lp.registry.model.milestonetag import MilestoneTag
        store = Store.of(self)
        return store.find(
            MilestoneTag, MilestoneTag.milestone_id == self.id
            ).order_by(MilestoneTag.tag)

    def getTags(self):
        """See IMilestone."""
        # Prevent circular references.
        from lp.registry.model.milestonetag import MilestoneTag
        return list(self.getTagsData().values(MilestoneTag.tag))


class MilestoneSet:
    implements(IMilestoneSet)

    def __iter__(self):
        """See lp.registry.interfaces.milestone.IMilestoneSet."""
        for ms in Milestone.select():
            yield ms

    def get(self, milestoneid):
        """See lp.registry.interfaces.milestone.IMilestoneSet."""
        result = list(self.getByIds([milestoneid]))
        if not result:
            raise NotFoundError(
                "Milestone with ID %d does not exist" % milestoneid)
        return result[0]

    def getByIds(self, milestoneids):
        """See `IMilestoneSet`."""
        return IStore(Milestone).find(Milestone,
            Milestone.id.is_in(milestoneids))

    def getByNameAndProduct(self, name, product, default=None):
        """See lp.registry.interfaces.milestone.IMilestoneSet."""
        query = AND(Milestone.q.name == name,
                    Milestone.q.productID == product.id)
        milestone = Milestone.selectOne(query)
        if milestone is None:
            return default
        return milestone

    def getByNameAndDistribution(self, name, distribution, default=None):
        """See lp.registry.interfaces.milestone.IMilestoneSet."""
        query = AND(Milestone.q.name == name,
                    Milestone.q.distributionID == distribution.id)
        milestone = Milestone.selectOne(query)
        if milestone is None:
            return default
        return milestone

    def getVisibleMilestones(self):
        """See lp.registry.interfaces.milestone.IMilestoneSet."""
        return Milestone.selectBy(active=True, orderBy='id')


class ProjectMilestone(MilestoneData, HasBugsBase):
    """A virtual milestone implementation for project.

    The current database schema has no formal concept of milestones related to
    projects. A milestone named `milestone` is considered to belong to
    a project if the project contains at least one product with a milestone
    of the same name. A project milestone is considered to be active if at
    least one product milestone with the same name is active.  The
    `dateexpected` attribute of a project milestone is set to the minimum of
    the `dateexpected` values of the product milestones.
    """

    implements(IProjectGroupMilestone)

    def __init__(self, target, name, dateexpected, active):
        self.code_name = None
        # The id is necessary for generating a unique memcache key
        # in a page template loop. The ProjectMilestone.id is passed
        # in as the third argument to the "cache" TALes.
        self.id = 'ProjectGroup:%s/Milestone:%s' % (target.name, name)
        self.name = name
        self.target = target
        self.code_name = None
        self.product = None
        self.distribution = None
        self.productseries = None
        self.distroseries = None
        self.product_release = None
        self.dateexpected = dateexpected
        self.active = active
        self.series_target = None
        self.summary = None

    @property
    def specifications(self):
        """See `IMilestoneData`."""
        from lp.registry.model.person import Person
        from lp.registry.model.product import Product
        store = Store.of(self.target)
        origin = [
            Specification,
            LeftJoin(
                SpecificationWorkItem,
                SpecificationWorkItem.specification_id == Specification.id),
            Join(Milestone,
                 Or(Milestone.id == Specification.milestoneID,
                    Milestone.id == SpecificationWorkItem.milestone_id)),
            Join(Product, Product.id == Milestone.productID),
            LeftJoin(Person, Specification.assigneeID == Person.id),
            ]

        results = store.using(*origin).find(
            (Specification, Person),
            Product.projectID == self.target.id,
            Milestone.name == self.name,
            Or(SpecificationWorkItem.deleted == None,
               SpecificationWorkItem.deleted == False))
        results.config(distinct=True)
        ordered_results = results.order_by(Desc(Specification.priority),
                                           Specification.definition_status,
                                           Specification.implementation_status,
                                           Specification.title)
        mapper = lambda row: row[0]
        return DecoratedResultSet(ordered_results, mapper)

    @property
    def displayname(self):
        """See IMilestone."""
        return "%s %s" % (self.target.displayname, self.name)

    @property
    def title(self):
        """See IMilestone."""
        return self.displayname

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this milestone."""
        search_params.milestone = self

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.target.official_bug_tags

    def userHasBugSubscriptions(self, user):
        """See `IStructuralSubscriptionTarget`."""
        return False
