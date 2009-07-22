# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = ['BountySubscriptionNavigation']

from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.interfaces import IBountySubscription


class BountySubscriptionNavigation(GetitemNavigation):

    usedfor = IBountySubscription

