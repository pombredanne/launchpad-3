# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Milestone',
           'MilestoneSet',
           'ProjectMilestone',
           'ProjectMilestoneSet']

from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, AND, SQLObjectNotFound, BoolCol, DateCol,
    SQLMultipleJoin)

from canonical.launchpad.interfaces import (
    IMilestone, IMilestoneSet, IProjectMilestone, IProjectMilestoneSet,
    NotFoundError)
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.launchpad.database.specification import Specification


class Milestone(SQLBase):
    implements(IMilestone)

    # XXX: Guilherme Salgado 2007-03-27 bug=40978:
    # Milestones should be associated with productseries/distroseriess
    # so these columns are not needed.
    product = ForeignKey(dbName='product',
        foreignKey='Product', default=None)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', default=None)

    productseries = ForeignKey(dbName='productseries',
        foreignKey='ProductSeries', default=None)
    distroseries = ForeignKey(dbName='distrorelease',
        foreignKey='DistroSeries', default=None)
    name = StringCol(notNull=True)
    dateexpected = DateCol(notNull=False, default=None)
    visible = BoolCol(notNull=True, default=True)

    # joins
    specifications = SQLMultipleJoin('Specification', joinColumn='milestone',
        orderBy=['-priority', 'definition_status',
                 'implementation_status', 'title'],
        prejoins=['assignee'])

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
        if self.dateexpected:
            title += ' due ' + self.dateexpected.strftime('%Y-%m-%d')
        return title


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


class ProjectMilestone:
    """A virtual milestone implementation for project.

    The current database schema has no formal concept of milestones related to
    projects. A milestone named `milestone` is considererd to belong to
    a project if the project contains at least one product with a milestone
    of the same name. A project milestone is considered to be visible if at
    least one product milestone with the same name is visible.  The
    `dateexpected` attribute of a project milestone is set to the minimum of
    the `dateexpected` values of the product milestones.
    """

    implements(IProjectMilestone)

    is_project_milestone = True

    def __init__(self, target, name, dateexpected, visible):
        self.name = name
        self.id = None
        self.product = None
        self.distribution = None
        self.productseries = None
        self.distroseries = None
        self.dateexpected = dateexpected
        self.visible = visible
        self.target = target
        self.series_target = None

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
        """See `IMilestone`."""
        return self.name

    @property
    def title(self):
        title = 'Milestone %s' % self.name
        if self.dateexpected:
            title += ' due ' + self.dateexpected.strftime('%Y-%m-%d')
        return title


class ProjectMilestoneSet:
    implements(IProjectMilestoneSet)

    def getMilestonesForProject(
        self, project, only_visible=True, milestone_name=None):
        """See `IProjectMilestoneSet`."""
        having_clause = []
        if only_visible:
            having_clause.append("bool_or(Milestone.visible)=True")
        if milestone_name is not None:
            having_clause.append(
                "Milestone.name=%s" % sqlvalues(milestone_name))
        if having_clause:
            having_clause = 'HAVING ' + ' AND '.join(having_clause)
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
            """ % (sqlvalues(project)[0], having_clause)
        cur = cursor()
        cur.execute(query)
        result = cur.fetchall()
        return [ProjectMilestone(project, *row) for row in result]
