#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: b994d703-ccb8-415b-bbf8-ab31cb40d534
"""Parse and compare Debian version strings.

This module contains a class designed to sit in your Python code pretty
naturally and represent a Debian version string.  It implements various
special methods to make dealing with them sweet.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import re


# Regular expressions make validating things easy
valid_epoch = re.compile(r'^[0-9]+$')
valid_upstream = re.compile(r'^[0-9][A-Za-z0-9+:.-]*$')
valid_revision = re.compile(r'^[A-Za-z0-9+.]+$')

# Character comparison table for upstream and revision components
cmp_table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-.:"


class VersionError(Exception): pass
class BadInputError(VersionError): pass
class BadEpochError(BadInputError): pass
class BadUpstreamError(BadInputError): pass
class BadRevisionError(BadInputError): pass

class Version(object):
    """Debian version number.

    This class is designed to be reasonably transparent and allow you
    to write code like:

    |   s.version >= "1.100-1"

    The comparison will be done according to Debian rules, so "1.2" will
    compare lower.

    Properties:
      epoch       Epoch
      upstream    Upstream version
      revision    Debian/local revision
    """

    def __init__(self, ver):
        """Parse a string or number into the three components."""
        self.epoch = 0
        self.upstream = None
        self.revision = None

        ver = str(ver)
        if not len(ver):
            raise BadInputError, "Input cannot be empty"

        # Epoch is component before first colon
        idx = ver.find(":")
        if idx != -1:
            self.epoch = ver[:idx]
            if not len(self.epoch):
                raise BadEpochError, "Epoch cannot be empty"
            if not valid_epoch.search(self.epoch):
                raise BadEpochError, "Bad epoch format"
            ver = ver[idx+1:]

        # Revision is component after last hyphen
        idx = ver.rfind("-")
        if idx != -1:
            self.revision = ver[idx+1:]
            if not len(self.revision):
                raise BadRevisionError, "Revision cannot be empty"
            if not valid_revision.search(self.revision):
                raise BadRevisionError, "Bad revision format"
            ver = ver[:idx]

        # Remaining component is upstream
        self.upstream = ver
        if not len(self.upstream):
            raise BadUpstreamError, "Upstream version cannot be empty"
        if not valid_upstream.search(self.upstream):
            raise BadUpstreamError, "Bad upstream version format"

        self.epoch = int(self.epoch)

    def epochal(self):
        """Return the version without the epoch."""
        str = self.upstream
        if self.revision is not None:
            str += "-%s" % (self.revision,)
        return str

    def __str__(self):
        """Return the class as a string for printing."""
        str = ""
        if self.epoch > 0:
            str += "%d:" % (self.epoch,)
        str += self.upstream
        if self.revision is not None:
            str += "-%s" % (self.revision,)
        return str

    def __repr__(self):
        """Return a debugging representation of the object."""
        return "<%s epoch: %d, upstream: %s, revision: %s>" \
               % (self.__class__.__name__, self.epoch,
                  repr(self.upstream), repr(self.revision))

    def __cmp__(self, other):
        """Compare two Version classes."""
        other = Version(other)

        result = cmp(self.epoch, other.epoch)
        if result != 0: return result

        result = deb_cmp(self.upstream, other.upstream)
        if result != 0: return result

        result = deb_cmp(self.revision or "", other.revision or "")
        if result != 0: return result

        return 0


def strcut(str, idx, accept):
    """Cut characters from str that are entirely in accept."""
    ret = ""
    while idx < len(str) and str[idx] in accept:
        ret += str[idx]
        idx += 1

    return (ret, idx)

def deb_cmp_str(x, y):
    """Compare two strings in a deb version."""
    idx = 0
    while idx < len(x):
        if idx >= len(y): return 1

        result = cmp(cmp_table.index(x[idx]), cmp_table.index(y[idx]))
        if result != 0: return result

        idx += 1
    else:
        if idx < len(y): return -1

    return 0

def deb_cmp(x, y):
    """Implement the string comparison outlined by Debian policy."""
    x_idx = y_idx = 0
    while x_idx < len(x) or y_idx < len(y):
        # Compare strings
        (x_str, x_idx) = strcut(x, x_idx, cmp_table)
        (y_str, y_idx) = strcut(y, y_idx, cmp_table)
        result = deb_cmp_str(x_str, y_str)
        if result != 0: return result

        # Compare numbers
        (x_str, x_idx) = strcut(x, x_idx, "0123456789")
        (y_str, y_idx) = strcut(y, y_idx, "0123456789")
        result = cmp(int(x_str or "0"), int(y_str or "0"))
        if result != 0: return result

    return 0
