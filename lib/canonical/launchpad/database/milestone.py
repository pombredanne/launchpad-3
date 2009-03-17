# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212
"""Milestone model classes."""

__metaclass__ = type
__all__ = [
    'HasMilestonesMixin',
    'Milestone',
    'MilestoneSet',
    'ProjectMilestone',
    'milestone_sort_key',
    ]

import datetime

from zope.component import getUtility
from zope.interface import implements

from sqlobject import (
    AND, BoolCol, DateCol, ForeignKey, SQLMultipleJoin, SQLObjectNotFound,
    StringCol)
from storm.locals import And, Store

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.sorting import expand_numbers
from canonical.launchpad.database.bugtarget import HasBugsBase
from canonical.launchpad.database.specification import Specification
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscriptionTargetMixin)
from canonical.launchpad.interfaces.bugtask import (
    BugTaskSearchParams, IBugTaskSet)
from canonical.launchpad.interfaces.bugtarget import IHasBugs
from canonical.launchpad.interfaces.milestone import (
    IHasMilestones, IMilestone, IMilestoneSet, IProjectMilestone)
from canonical.launchpad.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget)
from canonical.launchpad.webapp.interfaces import NotFoundError


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

    def _getMilestoneCondition(self):
        """Provides condition for milestones and all_milestones properties.

        Subclasses need to override this method.

        :return: Storm ComparableExpr object.
        """
        raise NotImplementedError(
            "Unexpected class for mixin: %r" % self)

    @property
    def all_milestones(self):
        """See `IHasMilestones`."""
        store = Store.of(self)
        result = store.find(Milestone, self._getMilestoneCondition())
        return sorted(result, key=milestone_sort_key, reverse=True)

    @property
    def milestones(self):
        """See `IHasMilestones`."""
        store = Store.of(self)
        result = store.find(Milestone,
                            And(self._getMilestoneCondition(),
                                Milestone.active == True))
        return sorted(result, key=milestone_sort_key, reverse=True)


class Milestone(SQLBase, StructuralSubscriptionTargetMixin, HasBugsBase):
    implements(IHasBugs, IMilestone, IStructuralSubscriptionTarget)

    # XXX: Guilherme Salgado 2007-03-27 bug=40978:
    # Milestones should be associated with productseries/distroseriess
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
    # XXX: EdwinGrubbs 2009-02-06 bug=326384:
    # The Milestone.dateexpected should be changed into a date column,
    # since the class defines the field as a DateCol, so that a list of
    # milestones can't have some dateexpected attributes that are
    # datetimes and others that are dates, which can't be compared.
    dateexpected = DateCol(notNull=False, default=None)
    active = BoolCol(notNull=True, default=True)
    summary = StringCol(notNull=False, default=None)
    code_name = StringCol(dbName='codename', notNull=False, default=None)

    # joins
    specifications = SQLMultipleJoin('Specification', joinColumn='milestone',
        orderBy=['-priority', 'definition_status',
                 'implementation_status', 'title'],
        prejoins=['assignee'])

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
    def target(self):
        """See IMilestone."""
        if self.product:
            return self.product
        elif self.distribution:
            return self.distribution

    @property
    def series_target(self):
        """See IMilestone."""
        if self.productseries:
            return self.productseries
        elif self.distroseries:
            return self.distroseries

    @property
    def displayname(self):
        """See IMilestone."""
        return "%s: %s" % (self.target.displayname, self.name)

    @property
    def title(self):
        """See IMilestone."""
        title = 'Milestone %s for %s' % (self.name, self.target.displayname)
        return title

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
            raise AssertionError(
                'A milestone can only have one Productrelease.')
        return ProductRelease(
            owner=owner,
            changelog=changelog,
            release_notes=release_notes,
            datereleased=datereleased,
            milestone=self)

    def destroySelf(self):
        """See `IMilestone`."""
        params = BugTaskSearchParams(milestone=self, user=None)
        bugtasks = getUtility(IBugTaskSet).search(params)
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


class MilestoneSet:
    implements(IMilestoneSet)

    def __iter__(self):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        for ms in Milestone.select():
            yield ms

    def get(self, milestoneid):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        try:
            return Milestone.get(milestoneid)
        except SQLObjectNotFound, err:
            raise NotFoundError(
                "Milestone with ID %d does not exist" % milestoneid)

    def getByNameAndProduct(self, name, product, default=None):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        query = AND(Milestone.q.name==name,
                    Milestone.q.productID==product.id)
        milestone = Milestone.selectOne(query)
        if milestone is None:
            return default
        return milestone

    def getByNameAndDistribution(self, name, distribution, default=None):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        query = AND(Milestone.q.name==name,
                    Milestone.q.distributionID==distribution.id)
        milestone = Milestone.selectOne(query)
        if milestone is None:
            return default
        return milestone


class ProjectMilestone(HasBugsBase):
    """A virtual milestone implementation for project.

    The current database schema has no formal concept of milestones related to
    projects. A milestone named `milestone` is considererd to belong to
    a project if the project contains at least one product with a milestone
    of the same name. A project milestone is considered to be active if at
    least one product milestone with the same name is active.  The
    `dateexpected` attribute of a project milestone is set to the minimum of
    the `dateexpected` values of the product milestones.
    """

    implements(IProjectMilestone)

    def __init__(self, target, name, dateexpected, active):
        self.name = name
        self.id = None
        self.product = None
        self.distribution = None
        self.productseries = None
        self.distroseries = None
        self.dateexpected = dateexpected
        self.active = active
        self.target = target
        self.series_target = None
        self.summary = None

    @property
    def specifications(self):
        """See `IMilestone`."""
        return Specification.select(
            """milestone IN
                (SELECT milestone.id
                    FROM Milestone, Product
                    WHERE Milestone.Product = Product.id
                    AND Milestone.name = %s
                    AND Product.project = %s)
            """ % sqlvalues(self.name, self.target),
            orderBy=['-priority', 'definition_status',
                     'implementation_status', 'title'],
            prejoins=['assignee'])

    @property
    def displayname(self):
        """See IMilestone."""
        return "%s: %s" % (self.target.displayname, self.name)

    @property
    def title(self):
        """See IMilestone."""
        title = 'Milestone %s for %s' % (self.name, self.target.displayname)
        if self.dateexpected:
            title += ' due ' + self.dateexpected.strftime('%Y-%m-%d')
        return title

    def _customizeSearchParams(self, search_params):
        """Customize `search_params` for this milestone."""
        search_params.milestone = self

    @property
    def official_bug_tags(self):
        """See `IHasBugs`."""
        return self.target.official_bug_tags

