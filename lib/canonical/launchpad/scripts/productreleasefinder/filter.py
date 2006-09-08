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
        regexp = fnmatch.translate(self.base_url + self.glob)
        # Use the same hack as distutils does so that "*" and "?" in
        # globs do not match slashes.
        regexp = re.sub(r'(^|[^\\])\.', r'\1[^/]', regexp)
        self.pattern = re.compile(regexp)

    def match(self, url):
        """Returns true if this filter pattern matches the URL."""
        return bool(self.pattern.match(url))
