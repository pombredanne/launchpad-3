# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Update Product.remote_product using BugWatch information."""

__metaclass__ = type
__all__ = ['RemoteProductUpdater']

from zope.component import getUtility

from canonical.launchpad.components.externalbugtracker import (
    BugWatchUpdateError, BugWatchUpdateWarning, get_external_bugtracker)
from canonical.launchpad.interfaces.bugtracker import (
    BugTrackerType, SINGLE_PRODUCT_BUGTRACKERTYPES)
from canonical.launchpad.interfaces.product import IProductSet


class RemoteProductUpdater:
    """Updates Product.remote_product."""

    def __init__(self, txn, logger):
        self.txn = txn
        self.logger = logger

    def _getExternalBugTracker(self, bug_tracker):
        """Get the IExternalBugTracker for the given bug tracker."""
        return get_external_bugtracker(bug_tracker)

    def update(self):
        """Update `remote_product` for all Products it can be set for."""
        # We can't interact with an e-mail address, so don't try to
        # update products with such trackers.
        types_to_exclude = (
            SINGLE_PRODUCT_BUGTRACKERTYPES + [BugTrackerType.EMAILADDRESS])
        multi_product_trackers = [
            bugtracker_type for bugtracker_type in BugTrackerType.items
            if bugtracker_type not in types_to_exclude]

        for bugtracker_type in multi_product_trackers:
            self.updateByBugTrackerType(bugtracker_type)

    def updateByBugTrackerType(self, bugtracker_type):
        """Update `remote_product` for Products using the bug tracker type.

        The `remote_product` attribute is only updated if it's None.
        """
        product_set = getUtility(IProductSet)
        products_needing_updating = list(
            product_set.getProductsWithNoneRemoteProduct(bugtracker_type))
        self.logger.info("%s projects using %s needing updating." % (
            len(products_needing_updating), bugtracker_type.name))
        for product in products_needing_updating:
            self.logger.debug("Trying to update %s" % product.name)
            # Pick an arbitrary bug watch for the product. They all
            # should point to the same product in the external bug
            # tracker. We could do some sampling to make it more
            # reliable, but it's not worth the trouble.
            bug_watch = product.getLinkedBugWatches().any()
            if bug_watch is None:
                self.logger.debug("No bug watches for %s" % product.name)
                # No bug watches have been created for this product, so
                # we can't figure out what remote_product should be.
                continue
            external_bugtracker = self._getExternalBugTracker(
                bug_watch.bugtracker)

            try:
                external_bugtracker.initializeRemoteBugDB(
                    [bug_watch.remotebug])
                remote_product = external_bugtracker.getRemoteProduct(
                    bug_watch.remotebug)
            except (BugWatchUpdateError, BugWatchUpdateWarning), error:
                self.logger.error(
                    "Unable to set remote_product for '%s': %s" %
                    (product.name, error))
                continue

            self.logger.info("Setting remote_product for %s to %r" % (
                product.name, remote_product))
            product.remote_product = remote_product
            self.txn.commit()
