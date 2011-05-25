# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""BugSummary interfaces."""

__metaclass__ = type
__all__ = ['IBugSummary']


from zope.interface import Interface
from zope.schema import (
    Choice,
    Int,
    Object,
    Text,
    )

from canonical.launchpad import _
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.milestone import IMilestone
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName


class IBugSummary(Interface):
    """Interface for BugSummary database class.

    All fields are readonly as this table is maintained by database
    triggers.
    """

    id = Int(readonly=True)
    count = Int(readonly=True)

    product_id = Int(readonly=True)
    product = Object(IProduct, readonly=True)

    productseries_id = Int(readonly=True)
    productseries = Object(IProductSeries, readonly=True)

    distribution_id = Int(readonly=True)
    distribution = Object(IDistribution, readonly=True)

    distroseries_id = Int(readonly=True)
    distroseries = Object(IDistroSeries, readonly=True)

    sourcepackagename_id = Int(readonly=True)
    sourcepackagename = Object(ISourcePackageName, readonly=True)

    viewed_by_id = Int(readonly=True)
    viewed_by = Object(IPerson, readonly=True)

    tag = Text(readonly=True)
    status = Choice(
        title=_('Status'), vocabulary=BugTaskStatus, readonly=True)

    milestone_id = Int(readonly=True)
    milestone = Object(IMilestone, readonly=True)
