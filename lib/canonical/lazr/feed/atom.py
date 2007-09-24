# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Base classes for Atom feeds.

Atom is a syndication format specified in RFC 4287.  It is an XML format
consisting of a feed and one or more entries.
"""

__metaclass__ = type

__all__ = [
    'AtomFeedBase',
    'AtomFeedEntry',
    'MINUTES',
    ]

import datetime


MINUTES = 60


class AtomFeedBase:
    """Base class for Atom feeds.

    The Atom syndication format is defined in RFC 4287.  A 'feed' is the outer
    container and MUST contain:
    - id - a universally unique and permanent URI.  May be the root of a web
    site address, e.g. http://launchpad.net
    - title - a human readable title for this feed.  It should not be blank.
    - updated - indicates the last time the feed was modified in a significant
    way.

    The feed may be extended with other items defined in a local namespace.

    Available attributes and methods are:

    - context
    - request
    - initialize()  <-- subclass this for specific initialization
    - getId()
    - getUpdated()
    - getTitle()
    - getURL()
    - getItems()
    - itemToAtomFeedEntry
    """

    max_age = 60 * MINUTES

    def __init__(self, context, request):
        self.context = context
        self.request = request
    def initialize(self):
        """Override this in subclasses.

        Default implementation does nothing.
        """
        pass
    def getTitle(self):
        pass
    def getURL(self):
        pass
    def getItems(self):
        pass
    def itemToAtomFeedEntry(self, item):
        pass


class AtomFeedEntry:
    """Base class for Atom feeds.

    Available attributes and methods are:

    - context
    - request
    - initialize()  <-- subclass this for specific initialization
    - user          <-- currently logged-in user
    - getTitle()
    - getURL()
    - getItems()
    - itemToAtomFeedEntry
    """
    pass
