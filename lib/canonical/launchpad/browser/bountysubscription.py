# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BountySubscriptionNavigation']

from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.interfaces import IBountySubscription


class BountySubscriptionNavigation(GetitemNavigation):

    usedfor = IBountySubscription

