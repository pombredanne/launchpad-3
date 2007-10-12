# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'FeedsNavigation',
    'FeedsRootUrlData'
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IBugTaskSet,
    IFeedsApplication,
    IPersonSet,
    IPillarNameSet,
    NotFoundError,
    )
from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp import (
    canonical_name, canonical_url, Navigation)
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

class FeedsRootUrlData:
    """ICanonicalUrlData for Feeds."""

    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = 'feeds'

    def __init__(self, context):
        self.context = context


class FeedsNavigation(Navigation):

    usedfor = IFeedsApplication

    newlayer = FeedsLayer

    stepto_utilities = {
        'bugs': IBugTaskSet,
        }

    def traverse(self, name):
        # XXX: statik 2007-10-09 bug=150941
        # Need to block pages not registered on the FeedsLayer

        if name in self.stepto_utilities:
            return getUtility(self.stepto_utilities[name])

        if name.startswith('~'):
            # redirect to the canonical name before doing the lookup
            if canonical_name(name) != name:
                return self.redirectSubTree(
                    canonical_url(self.context) + canonical_name(name),
                    status=301)
            else:
                person = getUtility(IPersonSet).getByName(name[1:])
                return person

        try:
            # redirect to the canonical name before doing the lookup
            if canonical_name(name) != name:
                return self.redirectSubTree(
                    canonical_url(self.context) + canonical_name(name),
                    status=301)
            else:
                return getUtility(IPillarNameSet)[name]

        except NotFoundError:
            return None

