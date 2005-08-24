"""URL filter.

This module implements the URL filtering to identify which glob each
filename matches, or whether it is a file outside of any known pattern.
"""

import os

from fnmatch import fnmatchcase
from urlparse import urlsplit, urljoin

from hct.util import log


class Filter(object):
    """URL filter.

    The filters dictionary maps a textual identity to a glob that the
    basename part of the URL's path will be checked against.  Each filter
    is a tuple of (base_url, glob) where the URL being checked must begin
    with the base_url before the glob is checked.
    """

    def __init__(self, filters={}, log_parent=None):
        self.log = log.get_logger("Filter", log_parent)
        self.filters = filters

    def check(self, url):
        """Check a URL against the filters.

        Checks the basename portion of the URL's path against each value
        in the filters dictionary, and returns the key of the first matching
        glob.
        """
        self.log.info("Checking %s", url)
        (scheme, netloc, path, query, fragment) = urlsplit(url)
        slash = path.rfind("/")
        if slash != -1:
            path = path[slash + 1:]
        self.log.debug("Filename portion is %s", path)

        for key, val in self.filters.items():
            (base_url, glob) = val
            if url.startswith(base_url) and fnmatchcase(path, glob):
                self.log.info("Matches %s glob (%s)", key, glob)
                return key
        else:
            self.log.info("No matches")
            return None


class Cache(object):
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
        (scheme, netloc, path, query, fragment) = urlsplit(url)
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
