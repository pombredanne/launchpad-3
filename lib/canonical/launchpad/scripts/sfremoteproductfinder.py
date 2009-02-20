# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Utilities for the sfremoteproductfinder cronscript"""

__metaclass__ = type
__all__ = [
    'SourceForgeRemoteProductFinder',
    ]

from urllib2 import urlopen

from zope.component import getUtility

from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities)
from canonical.launchpad.scripts.logger import log as default_log
from canonical.launchpad.webapp import urlappend


class SourceForgeRemoteProductFinder:
    """Responsible for finding the remote product of SourceForge projects."""

    def __init__(self, txn, logger=None):
        self.txn = txn
        self.logger = logger
        if logger is None:
            self.logger = default_log

        # We use the SourceForge celebrity to make sure that we're
        # always going to use the right URLs.
        self.sourceforge_baseurl = getUtility(
            ILaunchpadCelebrities).sourceforge_tracker.baseurl

    def _getPage(self, page):
        """GET the specified page on the remote HTTP server."""
        page_url = urlappend(self.sourceforge_baseurl, page)
        return urlopen(page_url).read()

    def getRemoteProductFromSourceForge(self, sf_project):
        """Return the remote product of a SourceForge project.

        :return: The group_id and atid of the SourceForge project's bug
            tracker as an ampersand-separated string in the form
            'group_id&atid'.
        """
        # First, fetch the project page.
        project_page = self._getPage("projects/%s" % sf_project)

    def setRemoteProductsFromSourceForge(self):
        """Find and set the remote product for SF-linked Products."""
        products_to_update = getUtility(
            IProductSet).getSFLinkedProductsWithNoneRemoteProduct()

        self.logger.info(
            "Updating %s Products using SourceForge project data" %
            products_to_update.count())

        for product in products_to_update:
            pass
