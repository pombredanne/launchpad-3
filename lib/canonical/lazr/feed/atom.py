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
    pass


class AtomFeedEntry:
    pass
