# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'FeedsNavigation',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IFeedsApplication, ILaunchpadRoot, IPillarNameSet, NotFoundError)
from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp import Navigation, stepto, canonical_url
from canonical.launchpad.webapp.batching import BatchNavigator


class FeedsNavigation(Navigation):

    usedfor = IFeedsApplication

    newlayer = FeedsLayer

    def traverse(self, name):
        try:
            # XXX: FIXME: Redirect to lowercase before doing the lookup
            # bug 56646
            return getUtility(IPillarNameSet)[name.lower()]
        except NotFoundError:
            return None

