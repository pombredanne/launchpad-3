# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'LaunchpadContextMixin',
    ]

from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)


class LaunchpadContextMixin:
    """Mixin for classes which implement `ILaunchpadContext`."""

    def isWithin(self, context):
        """See `ILaunchpadContext`."""
        if IProduct.providedBy(self):
            return context == self or context == self.project
        elif IDistributionSourcePackage.providedBy(self):
            return context == self or context == self.distribution
        else:
            # This context can't be within any other context.
            return context == self
