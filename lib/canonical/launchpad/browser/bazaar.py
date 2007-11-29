# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View support classes for the bazaar application."""

__metaclass__ = type

__all__ = [
    'BazaarApplicationView',
    'BazaarApplicationNavigation',
    'BazaarProductView',
    ]

from datetime import datetime

from zope.component import getUtility

import bzrlib

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.lp import decorates

from canonical.launchpad.interfaces import (
    IBazaarApplication, IBranchSet, IProduct, IProductSet, IProductSeriesSet)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp import (
    ApplicationMenu, enabled_with_permission, LaunchpadView, Link, Navigation,
    stepto)
import canonical.launchpad.layers


class BazaarBranchesMenu(ApplicationMenu):
    usedfor = IBazaarApplication
    facet = 'branches'
    links = ['importer']

    @enabled_with_permission('launchpad.Admin')
    def importer(self):
        target = 'series/'
        text = 'Branch importer'
        summary = 'Manage CVS and SVN Trunk Imports'
        return Link(target, text, summary, icon='branch')


class BazaarApplicationView(LaunchpadView):

    @cachedproperty
    def series_set(self):
        return getUtility(IProductSeriesSet)

    def branch_count(self):
        return getUtility(IBranchSet).count()

    def product_count(self):
        return getUtility(IProductSet).getProductsWithBranches().count()

    def branches_with_bugs_count(self):
        return getUtility(IBranchSet).countBranchesWithAssociatedBugs()

    def import_count(self):
        return self.series_set.searchImports().count()

    @cachedproperty
    def bzr_version(self):
        return bzrlib.__version__

    @cachedproperty
    def recently_changed_branches(self):
        """Return the five most recently changed branches."""
        return list(getUtility(IBranchSet).getRecentlyChangedBranches(
            5, visible_by_user=self.user))

    @cachedproperty
    def recently_imported_branches(self):
        """Return the five most recently imported branches."""
        return list(getUtility(IBranchSet).getRecentlyImportedBranches(
            5, visible_by_user=self.user))

    @cachedproperty
    def recently_registered_branches(self):
        """Return the five most recently registered branches."""
        return list(getUtility(IBranchSet).getRecentlyRegisteredBranches(
            5, visible_by_user=self.user))

    @cachedproperty
    def short_product_tag_cloud(self):
        """Show a preview of the product tag cloud."""
        return BazaarProductView().products(
            num_products=config.launchpad.code_homepage_product_cloud_size)


class BazaarApplicationNavigation(Navigation):

    usedfor = IBazaarApplication

    newlayer = canonical.launchpad.layers.CodeLayer

    @stepto('series')
    def series(self):
        return getUtility(IProductSeriesSet)


class ProductInfo:

    decorates(IProduct, 'product')

    def __init__(self, product, num_branches, branch_size, elapsed, important):
        self.product = product
        self.num_branches = num_branches
        self.branch_size = branch_size
        self.elapsed_since_commit = elapsed
        self.important = important

    @property
    def branch_class(self):
        return "cloud-size-%s" % self.branch_size

    @property
    def time_darkness(self):
        if self.elapsed_since_commit is None:
            return "light"
        if self.elapsed_since_commit.days < 7:
            return "dark"
        if self.elapsed_since_commit.days < 31:
            return "medium"
        return "light"

    @property
    def branch_highlight(self):
        """Return 'highlight' or 'shade'."""
        if self.important:
            return 'highlight'
        else:
            return 'shade'

    @property
    def html_class(self):
        return "%s cloud-%s-%s" % (
            self.branch_class, self.branch_highlight, self.time_darkness)

    @property
    def html_title(self):
        if self.num_branches == 1:
            size = "1 branch"
        else:
            size = "%d branches" % self.num_branches
        if self.elapsed_since_commit is None:
            commit = "no commits yet"
        elif self.elapsed_since_commit.days == 0:
            commit = "last commit less than a day old"
        elif self.elapsed_since_commit.days == 1:
            commit = "last commit one day old"
        else:
            commit = "last commit %d days old" % self.elapsed_since_commit.days
        return "%s, %s" % (size, commit)


class BazaarProductView:
    """Browser class for products gettable with Bazaar."""

    def products(self, num_products=None):
        # XXX: TimPenhey 2007-02-26
        # sabdfl really wants a page that has all the products with code
        # on it.  I feel that at some stage it will just look too cumbersome,
        # and we'll want to optimise the view somehow, either by taking
        # a random sample of the products with code, or some other method
        # of reducing the full set of products.
        # As far as query efficiency goes, constructing 1k products is
        # sub-second, and the query to get the branch count and last commit
        # time runs in approximately 50ms on a vacuumed branch table.
        product_set = getUtility(IProductSet)
        products = shortlist(product_set.getProductsWithBranches(num_products),
                             2000, hardlimit=3000)

        # Any product that has a defined user branch for the development
        # product series is shown in another colour.  Given the above
        # query, all the products will be in the cache anyway.
        user_branch_products = set(
            [product.id for product in
             product_set.getProductsWithUserDevelopmentBranches()])

        branch_set = getUtility(IBranchSet)
        branch_summaries = branch_set.getActiveUserBranchSummaryForProducts(
            products)
        # Choose appropriate branch counts so we have an evenish distribution.
        counts = sorted([
            summary['branch_count'] for summary in branch_summaries.values()])
        # Lowest half are small.
        small_count = counts[len(counts)/2]
        # Top 20% are big.
        large_count = counts[-(len(counts)/5)]

        items = []
        now = datetime.today()
        for product in products:
            summary = branch_summaries.get(product)
            if not summary:
                # If the only branches for the product were import branches or
                # merged or abandoned branches, then there will not be a
                # summary returned for that product, and we are not interested
                # in showing them in our cloud.
                continue
            last_commit = summary['last_commit']
            if last_commit is None:
                elapsed = None
            else:
                elapsed = now - last_commit

            num_branches = summary['branch_count']
            if num_branches <= small_count:
                branch_size = 'small'
            elif num_branches > large_count:
                branch_size = 'large'
            else:
                branch_size = 'medium'

            important = product.id in user_branch_products

            items.append(ProductInfo(
                product, num_branches, branch_size, elapsed, important))

        return items
