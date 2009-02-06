# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View support classes for the bazaar application."""

__metaclass__ = type

__all__ = [
    'BazaarApplicationView',
    'BazaarProductView',
    ]

from datetime import datetime

from zope.component import getUtility

import bzrlib

from canonical.cachedproperty import cachedproperty
from canonical.config import config

from canonical.launchpad.interfaces.branch import IBranchSet
from canonical.launchpad.interfaces.codeimport import ICodeImportSet
from canonical.launchpad.interfaces.launchpad import IBazaarApplication
from canonical.launchpad.interfaces.product import IProduct, IProductSet
from canonical.launchpad.webapp import (
    ApplicationMenu, enabled_with_permission, LaunchpadView, Link)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)

from lazr.delegates import delegates

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

    @property
    def branch_count(self):
        return getUtility(IBranchSet).count()

    @property
    def product_count(self):
        return getUtility(IProductSet).getProductsWithBranches().count()

    @property
    def branches_with_bugs_count(self):
        return getUtility(IBranchSet).countBranchesWithAssociatedBugs()

    @property
    def import_count(self):
        return getUtility(ICodeImportSet).getActiveImports().count()

    @property
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


class ProductInfo:

    delegates(IProduct, 'product')

    def __init__(
        self, product, num_branches, branch_size, elapsed, important):
        self.product = product
        self.num_branches = num_branches
        self.branch_size = branch_size
        self.elapsed_since_commit = elapsed
        self.important = important

    @classmethod
    def _findProductInfo(cls, num_products):
        """Get products with their branch activity information.

        :return: a `ResultSet` of (product, num_branches, last_revision_date).
        """
        from canonical.launchpad.database import Branch, Product, Revision
        from canonical.launchpad.interfaces.branch import BranchType
        from storm.locals import Count, Max, Or
        # It doesn't matter if this query is even a whole day out of date, so
        # use the slave store.
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        # Get all products, the count of all hosted & mirrored branches and
        # the last revision date.
        result = store.find(
            (Product, Count(Branch.id), Max(Revision.revision_date)),
            Branch.product == Product.id,
            Or(Branch.branch_type == BranchType.HOSTED,
               Branch.branch_type == BranchType.MIRRORED),
            Branch.last_scanned_id == Revision.revision_id).group_by(Product)
        if num_products:
            result.config(limit=num_products)
        return result.order_by(Count(Branch.id))

    @classmethod
    def getProductInfo(cls, num_products=None):
        product_info = sorted(
            list(cls._findProductInfo(num_products)),
            key=lambda data: data[0].name)
        now = datetime.today()
        counts = sorted(zip(*product_info)[1])
        # Lowest half are small.
        small_count = counts[len(counts)/2]
        # Top 20% are big.
        large_count = counts[-(len(counts)/5)]
        for product, num_branches, last_revision_date in product_info:
            # Projects with no branches are not interesting.
            if num_branches == 0:
                continue
            if num_branches > large_count:
                branch_size = 'large'
            elif num_branches < small_count:
                branch_size = 'small'
            else:
                branch_size = 'medium'
            elapsed = now - last_revision_date
            # We want to highlight products that actually _use_ Launchpad.
            important = product.official_codehosting
            yield cls(product, num_branches, branch_size, elapsed, important)


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
            commit = (
                "last commit %d days old" % self.elapsed_since_commit.days)
        return "%s, %s" % (size, commit)


class BazaarProductView:
    """Browser class for products gettable with Bazaar."""

    def products(self, num_products=None):
        return ProductInfo.getProductInfo(num_products)
