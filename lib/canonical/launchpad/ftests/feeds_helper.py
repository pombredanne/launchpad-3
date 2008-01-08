# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for testing feeds."""

__metaclass__ = type
__all__ = [
    'IThing',
    'Thing',
    'ThingFeedView',
    ]


from zope.interface import implements, Interface, Attribute

from canonical.launchpad.webapp.publisher import LaunchpadView


class IThing(Interface):
    value = Attribute('the value of the thing')


class Thing(object):
    implements(IThing)

    def __init__(self, value):
        self.value = value

        def __repr__(self):
            return "<Thing '%s'>" % self.value


class ThingFeedView(LaunchpadView):
    usedfor = IThing
    feedname = "thing-feed"
    def __call__(self):
        return "a feed view on an IThing"
