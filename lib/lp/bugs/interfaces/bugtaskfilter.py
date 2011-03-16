# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fiter bugtasks based on context."""

__metaclass__ = type
__all__ = [
    'filter_bugtasks_by_context',
    ]

from collections import defaultdict, namedtuple
from operator import attrgetter

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage


OrderedBugTask = namedtuple('OrderedBugTask', 'rank id task')


class DistributionWeightCalculator:
    """Give higher weighing to tasks for the matching distribution."""

    def __init__(self, distribution):
        self.distributionID = distribution.id

    def __call__(self, bugtask):
        """Full weight is given to tasks for this distribution.

        Given that there must be a distribution task for a series of that
        distribution to have a task, we give no more weighting to a
        distroseries task than any other.
        """
        if bugtask.distributionID == self.distributionID:
            return OrderedBugTask(1, bugtask.id, bugtask)
        return OrderedBugTask(2, bugtask.id, bugtask)


class DistroSeriesWeightCalculator:
    """Try for the series first, the distro second, everything else third."""

    def __init__(self, distro_series):
        self.seriesID = distro_series.id
        self.distributionID = distro_series.distributionID

    def __call__(self, bugtask):
        """Full weight is given to tasks for this distro series.

        If the series isn't found, the distribution task is better than
        others.
        """
        if bugtask.distroseriesID == self.seriesID:
            return OrderedBugTask(1, bugtask.id, bugtask)
        elif bugtask.distributionID == self.distributionID:
            return OrderedBugTask(2, bugtask.id, bugtask)
        else:
            return OrderedBugTask(3, bugtask.id, bugtask)


class ProductWeightCalculator:
    """Give higher weighing to tasks for the matching product."""

    def __init__(self, product):
        self.productID = product.id

    def __call__(self, bugtask):
        """Full weight is given to tasks for this product.

        Given that there must be a product task for a series of that product
        to have a task, we give no more weighting to a productseries task than
        any other.
        """
        if bugtask.productID == self.productID:
            return OrderedBugTask(1, bugtask.id, bugtask)
        return OrderedBugTask(2, bugtask.id, bugtask)


class ProductSeriesWeightCalculator:
    """Try for the series first, the product second, everything else third."""

    def __init__(self, product_series):
        self.seriesID = product_series.id
        self.productID = product_series.productID

    def __call__(self, bugtask):
        """Full weight is given to tasks for this product series.

        If the series isn't found, the product task is better than others.
        """
        if bugtask.productseriesID == self.seriesID:
            return OrderedBugTask(1, bugtask.id, bugtask)
        elif bugtask.productID == self.productID:
            return OrderedBugTask(2, bugtask.id, bugtask)
        else:
            return OrderedBugTask(3, bugtask.id, bugtask)


class SourcePackageWeightCalculator:
    """This is the most complicated weight calculator.

    We look for the source package task, followed by the distro source
    package, then the distroseries task, and lastly the distro task.
    """

    def __init__(self, source_package):
        self.sourcepackagenameID = source_package.sourcepackagename.id
        self.seriesID = source_package.distroseries.id
        self.distributionID = source_package.distroseries.distributionID

    def __call__(self, bugtask):
        """Full weight is given to tasks for this source package.

        Failing that we try for the distro source package.
        """
        if bugtask.sourcepackagenameID == self.sourcepackagenameID:
            if bugtask.distroseriesID == self.seriesID:
                return OrderedBugTask(1, bugtask.id, bugtask)
            elif bugtask.distributionID == self.distributionID:
                return OrderedBugTask(2, bugtask.id, bugtask)
        elif bugtask.distroseriesID == self.seriesID:
            return OrderedBugTask(3, bugtask.id, bugtask)
        elif bugtask.distributionID == self.distributionID:
            return OrderedBugTask(4, bugtask.id, bugtask)
        # Catch the default case, and where there is a task for the same
        # sourcepackage on a different distro.
        return OrderedBugTask(5, bugtask.id, bugtask)


class SimpleWeightCalculator:
    """All tasks have the same weighting."""

    def __call__(self, bugtask):
        return OrderedBugTask(1, bugtask.id, bugtask)


def get_weight_calculator(context):
    """Create the appropriate weight calculator for the context.

    I did consider using adapters, but since this method is only called from
    this module, there didn't seem like any point.
    """
    if IProduct.providedBy(context):
        return ProductWeightCalculator(context)
    elif IProductSeries.providedBy(context):
        return ProductSeriesWeightCalculator(context)
    elif IDistribution.providedBy(context):
        return DistributionWeightCalculator(context)
    elif IDistroSeries.providedBy(context):
        return DistroSeriesWeightCalculator(context)
    elif ISourcePackage.providedBy(context):
        return SourcePackageWeightCalculator(context)
    else:
        return SimpleWeightCalculator()


def filter_bugtasks_by_context(context, bugtasks):
    """Return the bugtasks filtered so there is only one bug task per bug.

    The context is used to return the most relevent bugtask for that context.

    An initial constraint is to not require any database queries from this
    method.

    Current contexts that impact selection:
      IProduct
      IProductSeries
      IDistribution
      IDistroSeries
      ISourcePackage
    Others:
      get the first bugtask for any particular bug

    If the context is a Product, then return the product bug task if there is
    one.  If the context is a ProductSeries, then return the productseries
    task if there is one, and if there isn't, look for the product task.  A
    similar approach is taked for Distribution and distroseries.

    For source packages, we look for the source package task, followed by the
    distro source package, then the distroseries task, and lastly the distro
    task.

    If there is no specific matching task, we return the first task (the one
    with the smallest database id).
    """
    weight_calculator = get_weight_calculator(context)

    bug_mapping = defaultdict(list)
    for task in bugtasks:
        bug_mapping[task.bugID].append(weight_calculator(task))

    filtered = [sorted(tasks)[0].task for tasks in bug_mapping.itervalues()]
    return sorted(filtered, key=attrgetter('bugID'))
