# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Update Product.remote_product using BugWatch information."""

__metaclass__ = type
__all__ = ['RemoteProductUpdater']

from zope.component import getUtility

from canonical.launchpad.components.externalbugtracker import (
    get_external_bugtracker)
from canonical.launchpad.interfaces.product import IProductSet


class RemoteProductUpdater:
    """Updates Product.remote_product."""

    def __init__(self, txn):
        self.txn = txn

    def _getExternalBugTracker(self, bug_tracker):
        """Get the IExternalBugTracker for the given bug tracker."""
        return get_external_bugtracker(bug_tracker)

    def updateRemoteProduct(self, bugtracker_type):
        """Update `remote_product` for Products using the bug tracker type.

        The `remote_product` attribute is only updated if it's None.
        """
        product_set = getUtility(IProductSet)
        product_needing_updating = (
            product_set.getProductsWithNoneRemoteProduct(bugtracker_type))
        for product in products_needing_updating:
            # Pick an arbitrary bug watch for the product. They all
            # should point to the same product in the external bug
            # tracker. We could do some sampling to make it more
            # reliable, but it's not worth the trouble.
            bug_watch = product.getLinkedBugWatches().any()
            if bug_watch is None:
                # No bug watches have been created for this product, so
                # we can't figure out what remote_product should be.
                continue
            external_bugtracker = self._getExternalBugTracker(
                bug_watch.bugtracker)
            remote_product = external_bugtracker.getRemoteProduct(
                bug_watch.remotebug)
            product.remote_product = remote_product
            self.txn.commit()
