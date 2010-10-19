# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the BranchListingQueryOptimiser utility."""

__metaclass__ = type
__all__ = [
    'BranchListingQueryOptimiser',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.code.interfaces.branch import IBranchListingQueryOptimiser
from lp.code.model.seriessourcepackagebranch import SeriesSourcePackageBranch
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.sourcepackagename import SourcePackageName


class BranchListingQueryOptimiser:
    """Utility object for efficient DB queries for branch listings."""

    implements(IBranchListingQueryOptimiser)

    @staticmethod
    def getProductSeriesForBranches(branch_ids):
        """See `IBranchListingQueryOptimiser`."""
        # Since the branch listing renders the linked product series as
        # hyperlinks to the product series itself, and the canonical_url of
        # the product series traverses to the product, we can save ourselves
        # extra queries here by loading both the product and product series
        # objects.  These objects are then in the object cache, and not
        # queried again, but we only return the product series objects.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return [
            series for product, series in store.find(
                (Product, ProductSeries),
                ProductSeries.branchID.is_in(branch_ids),
                ProductSeries.product == Product.id).order_by(
                ProductSeries.name)]

    @staticmethod
    def getOfficialSourcePackageLinksForBranches(branch_ids):
        """See `IBranchListingQueryOptimiser`."""
        # Any real use of the official source package links is going to
        # traverse through the distro_series, distribution and
        # sourcepackagename objects.  For this reason, we get them all in the
        # one query, and only return the SeriesSourcePackageBranch objects.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        realise_objects = (
            Distribution, DistroSeries, SourcePackageName,
            SeriesSourcePackageBranch)
        return [
            link for distro, ds, spn, link in store.find(
                realise_objects,
                SeriesSourcePackageBranch.branchID.is_in(branch_ids),
                SeriesSourcePackageBranch.sourcepackagename ==
                SourcePackageName.id,
                SeriesSourcePackageBranch.distroseries ==
                DistroSeries.id,
                DistroSeries.distribution == Distribution.id)]
