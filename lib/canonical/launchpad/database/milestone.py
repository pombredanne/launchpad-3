# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Milestone', 'MilestoneSet']

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import (
    ForeignKey, StringCol, AND, SQLObjectNotFound, BoolCol, DateCol,
    MultipleJoin)

from canonical.launchpad.interfaces.milestone import IMilestone, IMilestoneSet
from canonical.database.sqlbase import SQLBase


class Milestone(SQLBase):
    implements(IMilestone)

    product = ForeignKey(dbName='product', foreignKey='Product')
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution')
    name = StringCol(notNull=True)
    dateexpected = DateCol(notNull=False, default=None)
    visible = BoolCol(notNull=True, default=True)

    # joins
    bugtasks = MultipleJoin('BugTask', joinColumn='milestone',
        orderBy=['-priority', '-datecreated', '-severity'])
    specifications = MultipleJoin('Specification', joinColumn='milestone',
        orderBy=['-priority', 'status', 'title'])

    @property
    def target(self):
        """See IMilestone."""
        if self.product:
            return self.product
        elif self.distribution:
            return self.distribution

    @property
    def displayname(self):
        """See IMilestone."""
        return 'Milestone %s' % self.name

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
        raise NotImplementedError

    def get(self, milestoneid):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        try:
            return Milestone.get(milestoneid)
        except SQLObjectNotFound, err:
            raise NotFoundError(
                "Milestone with ID %d does not exist" % milestoneid)

    def new(self, name, product=None, distribution=None, dateexpected=None,
        visible=True):
        """See IMilestoneSet."""
        return Milestone(name=name, product=product,
            distribution=distribution, dateexpected=dateexpected,
            visible=visible)


