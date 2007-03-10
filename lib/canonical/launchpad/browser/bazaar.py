# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View support classes for the bazaar application."""

__metaclass__ = type

__all__ = [
    'BazaarApplicationView',
    'BazaarApplicationNavigation',
    'BazaarProductView',
    ]

from datetime import datetime
import operator

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.lp import decorates

from canonical.launchpad.interfaces import (
    IBazaarApplication, IBranchSet, ILaunchpadCelebrities,
    IProduct, IProductSet, IProductSeriesSet)
from canonical.lp.dbschema import ImportStatus
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp import (
    ApplicationMenu, canonical_url, enabled_with_permission,
    Link, Navigation, stepto)
from canonical.launchpad.webapp.batching import BatchNavigator
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


class BazaarApplicationView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.seriesset = getUtility(IProductSeriesSet)

    def branch_count(self):
        return getUtility(IBranchSet).count()

    def product_count(self):
        return getUtility(IProductSet).getProductsWithBranches().count()

    def branches_with_bugs_count(self):
        return getUtility(IBranchSet).countBranchesWithAssociatedBugs()

    def import_count(self):
        return self.seriesset.importcount()

    def testing_count(self):
        return self.seriesset.importcount(ImportStatus.TESTING.value)

    def autotested_count(self):
        return self.seriesset.importcount(ImportStatus.AUTOTESTED.value)

    def testfailed_count(self):
        return self.seriesset.importcount(ImportStatus.TESTFAILED.value)

    def processing_count(self):
        return self.seriesset.importcount(ImportStatus.PROCESSING.value)

    def syncing_count(self):
        return self.seriesset.importcount(ImportStatus.SYNCING.value)

    def stopped_count(self):
        return self.seriesset.importcount(ImportStatus.STOPPED.value)

    @cachedproperty
    def recently_changed_branches(self):
        """Return the five most recently changed branches."""
        return list(getUtility(IBranchSet).getRecentlyChangedBranches(5))

    @cachedproperty
    def recently_imported_branches(self):
        """Return the five most recently imported branches."""
        return list(getUtility(IBranchSet).getRecentlyImportedBranches(5))

    @cachedproperty
    def recently_registered_branches(self):
        """Return the five most recently registered branches."""
        return list(getUtility(IBranchSet).getRecentlyRegisteredBranches(5))


class BazaarApplicationNavigation(Navigation):

    usedfor = IBazaarApplication

    newlayer = canonical.launchpad.layers.CodeLayer

    @stepto('series')
    def series(self):
        return getUtility(IProductSeriesSet)
 

class ProductInfo:
    
    decorates(IProduct, 'product')

    def __init__(self, product, branch_size, elapsed):
        self.product = product
        self.branch_size = branch_size
        self.elapsed_since_commit = elapsed

    @property
    def branch_class(self):
        return "cloud-size-%s" % self.branch_size

    @property
    def time_class(self):
        if self.elapsed_since_commit is None:
            return "cloud-shade-light"
        if self.elapsed_since_commit.days < 7:
            return "cloud-shade-dark"
        if self.elapsed_since_commit.days < 31:
            return "cloud-shade-medium"
        return "cloud-shade-light"

    @property
    def html_class(self):
        return "%s %s" % (self.branch_class, self.time_class)


class BazaarProductView:
    """Browser class for products gettable with Bazaar."""

    def products(self):
        # XXX: TimPenhey 2007-02-26
        # sabdfl really wants a page that has all the products with code
        # on it.  I feel that at some stage it will just look too cumbersome,
        # and we'll want to optimise the view somehow, either by taking
        # a random sample of the products with code, or some other method
        # of reducing the full set of products.
        # As far as query efficiency goes, constructing 1k products is
        # sub-second, and the query to get the branch count and last commit
        # time runs in approximately 50ms on a vacuumed branch table.
        products = shortlist(getUtility(IProductSet).getProductsWithBranches(),
                             1500, hardlimit=2000)
        
        branchset = getUtility(IBranchSet)
        branch_summaries = branchset.getBranchSummaryForProducts(products)
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
            summary = branch_summaries[product]
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
            
            items.append(ProductInfo(product, branch_size, elapsed))

        return items
    
