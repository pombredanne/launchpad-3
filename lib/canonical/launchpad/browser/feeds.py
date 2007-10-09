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
            # XXX: statik 2007-10-05  Redirect to lowercase before doing
            # the lookup bug 56646
            return getUtility(IPillarNameSet)[name.lower()]
        except NotFoundError:
            return None

