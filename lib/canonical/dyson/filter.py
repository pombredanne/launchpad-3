"""URL filter.

This module implements the URL filtering to identify which glob each
filename matches, or whether it is a file outside of any known pattern.
"""

__metaclass__ = type
__all__ = [
    'Filter',
    'FilterPattern',
    'Cache',
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


class Cache:
    """URL Cache.

    This class implements a simple cache of URLs on the filesystem.
    A URL can be checked using the Python 'in' keyword.
    """

    def __init__(self, path, log_parent=None):
        self.log = log.get_logger("Cache", log_parent)
        self.path = path
        self.files = {}

    def __contains__(self, url):
        """Check whether the cache contains the URL."""
        self.log.info("Checking cache for %s", url)
        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
        for bad in ("/", "."):
            path = path.replace(bad, "")

        cache_path = os.path.join(self.path, path[:2])
        self.log.debug("Cache file is %s", cache_path)

        if cache_path not in self.files:
            self.files[cache_path] = []
            if os.path.isfile(cache_path):
                self.log.debug("Loading cache file")
                f = open(cache_path, "r")
                try:
                    for line in f:
                        self.files[cache_path].append(line.strip())
                finally:
                    f.close()

        if url in self.files[cache_path]:
            self.log.info("Cache hit")
            return True
        else:
            self.files[cache_path].append(url)
            return False

    def save(self):
        """Save the cache."""
        if not os.path.isdir(self.path):
            os.mkdir(self.path)

        for cache_path, url_list in self.files.items():
            self.log.info("Saving cache file %s", cache_path)
            f = open(cache_path, "w")
            try:
                for url in url_list:
                    print >>f, url
            finally:
                f.close()
