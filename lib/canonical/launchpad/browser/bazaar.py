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

from canonical.launchpad.interfaces import (
    IBazaarApplication, IBranchSet, ILaunchpadCelebrities,
    IProductSet, IProductSeriesSet)
from canonical.lp.dbschema import ImportStatus
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

    def hct_count(self):
        branches = self.seriesset.search(forimport=True,
            importstatus=ImportStatus.SYNCING.value)
        count = 0
        for branch in branches:
            for package in branch.sourcepackages:
                if package.shouldimport:
                    count += 1
                    continue
        return count

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


class BazaarListItem:
    """A simple type that contains the display fields for the listing."""

    def __init__(self, product, branch_count, dev_branch, imported,
                 last_commit, elapsed_time):
        self.product = product
        self.branch_count = branch_count
        self.dev_branch = dev_branch
        self.imported = imported
        self.last_commit = last_commit
        self.elapsed_time = elapsed_time


class BazaarProductBatch(BatchNavigator):
    """Batch the listing as there are *many* products with branches."""

    def __init__(self, products, request):
        BatchNavigator.__init__(self, products, request)
        # Now fetch the details for the current batch.
        batch = self.currentBatch()
        branchset = getUtility(IBranchSet)
        self.branch_summaries = branchset.getBranchSummaryForProducts(batch)
        branches = branchset.getProductDevelopmentBranches(batch)
        self.dev_branches = dict(
            [(branch.product, branch) for branch in branches])

    def _createItem(self, product):
        """Returns the BazaarListItem for the product."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        summary = self.branch_summaries[product]
        branch = self.dev_branches.get(product)
        imported = branch and branch.owner == vcs_imports
        now = datetime.now()
        last_commit = summary['last_commit']
        elapsed = last_commit and (now - last_commit)
        return BazaarListItem(
            product, summary['branch_count'],
            branch, imported, last_commit, elapsed)
        
    def getViewableItems(self):
        return [self._createItem(product) for product in self.batch]
    

class BazaarProductView:
    """Browser class for products gettable with Bazaar."""

    @cachedproperty
    def listing(self):
        return BazaarProductBatch(
            getUtility(IProductSet).getProductsWithBranches(),
            self.request)
