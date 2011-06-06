# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugSummary Storm database classes."""

__metaclass__ = type
__all__ = ['BugSummary']

from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from lp.bugs.interfaces.bugsummary import IBugSummary
from lp.bugs.interfaces.bugtask import BugTaskStatus
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

    __storm_table__ = 'bugsummary'

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

    viewed_by_id = Int(name='viewed_by')
    viewed_by = Reference(viewed_by_id, Person.id)

    tag = Unicode()
    status = EnumCol(dbName='status', schema=BugTaskStatus)

    milestone_id = Int(name='milestone')
    milestone = Reference(milestone_id, Milestone.id)
