# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugSummary Storm database classes."""

__metaclass__ = type
__all__ = [
    'BugSummary',
    'CombineBugSummaryConstraint',
    ]

from storm.locals import (
    And,
    Bool,
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.enumcol import EnumCol
from lp.bugs.interfaces.bugsummary import (
    IBugSummary,
    IBugSummaryDimension,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    BugTaskStatusSearch,
    )
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.milestone import Milestone
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackagename import SourcePackageName


class BugSummary(Storm):
    """BugSummary Storm database class."""

    implements(IBugSummary)

    __storm_table__ = 'combinedbugsummary'

    id = Int(primary=True)
    count = Int()

    product_id = Int(name='product')
    product = Reference(product_id, Product.id)

    productseries_id = Int(name='productseries')
    productseries = Reference(productseries_id, ProductSeries.id)

    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, Distribution.id)

    distroseries_id = Int(name='distroseries')
    distroseries = Reference(distroseries_id, DistroSeries.id)

    sourcepackagename_id = Int(name='sourcepackagename')
    sourcepackagename = Reference(sourcepackagename_id, SourcePackageName.id)

    milestone_id = Int(name='milestone')
    milestone = Reference(milestone_id, Milestone.id)

    status = EnumCol(
        dbName='status',
        schema=(BugTaskStatus, BugTaskStatusSearch))

    importance = EnumCol(dbName='importance', schema=BugTaskImportance)

    tag = Unicode()

    viewed_by_id = Int(name='viewed_by')
    viewed_by = Reference(viewed_by_id, Person.id)

    has_patch = Bool()
    fixed_upstream = Bool()


class CombineBugSummaryConstraint:
    """A class to combine two separate bug summary constraints.

    This is useful for querying on multiple related dimensions (e.g. milestone
    + sourcepackage) - and essential when a dimension is not unique to a
    context.
    """

    implements(IBugSummaryDimension)

    def __init__(self, *dimensions):
        self.dimensions = map(
            lambda x:removeSecurityProxy(x.getBugSummaryContextWhereClause()),
            dimensions)

    def getBugSummaryContextWhereClause(self):
        """See `IBugSummaryDimension`."""
        return And(*self.dimensions)
