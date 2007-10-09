# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'FeedsNavigation',
    ]

from zope.component import getUtility
from zope.publisher.interfaces import NotFound

from canonical.launchpad.interfaces import (
    IFeedsApplication, IPillarNameSet, NotFoundError)
from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp import Navigation

class FeedsNavigation(Navigation):

    usedfor = IFeedsApplication

    newlayer = FeedsLayer

    def traverse(self, name):
        try:
            # XXX: statik 2007-10-05 bug=56646 Redirect to lowercase before 
            # doing the lookup
            # XXX: statik 2007-10-09 bug=150941
            # Need to block pages not registered on the FeedsLayer
            return getUtility(IPillarNameSet)[name.lower()]
        except NotFoundError:
            return None

