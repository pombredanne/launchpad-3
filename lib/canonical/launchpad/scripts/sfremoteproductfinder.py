# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Utilities for the sfremoteproductfinder cronscript"""

__metaclass__ = type
__all__ = [
    'SourceForgeRemoteProductFinder',
    ]

from urllib2 import urlopen

from zope.component import getUtility

from canonical.launchpad.interfaces.product import IProductSet


class SourceForgeRemoteProductFinder:
    """Responsible for finding the remote product of SourceForge projects."""

    def _getPage(self, page):
        """GET the specified page on the remote HTTP server."""
        return urlopen(page).read()
