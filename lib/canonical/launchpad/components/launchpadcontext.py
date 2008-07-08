# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'LaunchpadContainerMixin',
    ]

from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)


class LaunchpadContainerMixin:
    """Mixin for classes which implement `ILaunchpadContainer`."""

    def isWithin(self, context):
        """See `ILaunchpadContainer`."""
        return context == self
