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
            if name.startswith('~'):
                # redirect to the lower() version before doing the lookup
                if name.lower() != name:
                    return self.redirectSubTree(
                        canonical_url(self.context) + name.lower(), status=301)
                else:
                    personset = getUtility(IPersonSet)
                    person = personset.getByName(name[1:])
                    return person

            # XXX: statik 2007-10-09 bug=150941
            # Need to block pages not registered on the FeedsLayer

            # redirect to the lower() version before doing the lookup
            if name.lower() != name:
                return self.redirectSubTree(
                    canonical_url(self.context) + name.lower(), status=301)
            else:
                return getUtility(IPillarNameSet)[name]

        except NotFoundError:
            return None

