# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'FeedNavigation',
    ]


from canonical.launchpad.interfaces import (
    IFeedApplication)
from canonical.launchpad.layers import FeesdLayer
from canonical.launchpad.webapp import Navigation


class FeedNavigation(Navigation):

    usedfor = IFeedApplication

    newlayer = FeedsLayer
