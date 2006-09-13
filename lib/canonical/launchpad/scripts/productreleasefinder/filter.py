"""URL filter.

This module implements the URL filtering to identify which glob each
filename matches, or whether it is a file outside of any known pattern.
"""

__metaclass__ = type
__all__ = [
    'Filter',
    'FilterPattern',
    ]

import fnmatch
import os
import re
import urlparse

from hct.util import log


class Filter:
    """URL filter.

    The filters argument is a sequence of filter patterns.  Each
    filter pattern is an object with a match() method used to check if
    the pattern matches the URL.
    """

    def __init__(self, filters=(), log_parent=None):
        self.log = log.get_logger("Filter", log_parent)
        self.filters = list(filters)

    def check(self, url):
        """Check a URL against the filters.

        Checks each of the registered patterns against the given URL,
        and returns the 'key' attribute of the first pattern that
        matches.
        """
        self.log.info("Checking %s", url)
        for pattern in self.filters:
            if pattern.match(url):
                self.log.info("Matches %s glob (%s)",
                              pattern.key, pattern.glob)
                return pattern.key
        else:
            self.log.info("No matches")
            return None

    def containedBy(self, url):
        """Check if any filters could match children of a URL."""
        self.log.info("Checking if children of %s could match a pattern")
        for pattern in self.filters:
            if pattern.containedBy(url):
                self.log.info("Matches %s glob (%s)",
                              pattern.key, pattern.glob)
                return True
        else:
            self.log.info("No matches")
            return False


class FilterPattern:
    """A filter pattern.

    Instances of FilterPattern are intended to be used with a Filter
    instance.
    """

    def __init__(self, key, base_url, glob):
        self.key = key
        self.base_url = base_url
        self.glob = glob

        if not self.base_url.endswith('/'):
            self.base_url += '/'
        parts = (self.base_url + self.glob).split('/')
        self.patterns = [re.compile(fnmatch.translate(part)) for part in parts]

    def match(self, url):
        """Returns true if this filter pattern matches the URL."""
        parts = url.split('/')
        # If the length of list of slash separated parts of the URL
        # differs from the number of patterns, then they can't match.
        if len(parts) != len(self.patterns):
            return False
        for (part, pattern) in zip(parts, self.patterns):
            if not pattern.match(part):
                return False
        # Everything matches ...
        return True

    def containedBy(self, url):
        """Returns true if this pattern could match children of the URL."""
        url = url.rstrip('/')
        parts = url.split('/')
        # If the URL contains greater than or equal the number of
        # parts as the number of patterns we have, then it couldn't
        # contain any children that match this pattern.
        if len(parts) >= len(self.patterns):
            return False
        for (part, pattern) in zip(parts, self.patterns):
            if not pattern.match(part):
                return False
        # Everything else matches ...
        return True
