# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for testing feeds."""

__metaclass__ = type
__all__ = [
    'IThing',
    'Thing',
    'ThingFeedView',
    'parse_entries',
    'parse_ids',
    'parse_links',
    ]


from zope.interface import implements, Interface, Attribute
from BeautifulSoup import BeautifulStoneSoup as BSS
from BeautifulSoup import SoupStrainer

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


def parse_entries(contents):
    """Define a helper function for parsing feed entries."""
    strainer = SoupStrainer('entry')
    entries = [tag for tag in BSS(contents,
                                  parseOnlyThese=strainer)]
    return entries


def parse_links(contents, rel):
    """Define a helper function for parsing feed links."""
    strainer = SoupStrainer('link', rel=rel)
    entries = [tag for tag in BSS(contents,
                                  parseOnlyThese=strainer,
                                  selfClosingTags=['link'])]
    return entries


def parse_ids(contents):
    """Define a helper function for parsing ids."""
    strainer = SoupStrainer('id')
    ids = [tag for tag in BSS(contents,
                              parseOnlyThese=strainer)]
    return ids
