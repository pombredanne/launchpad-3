# Copyright 2006 Canonical Ltd.  All rights reserved.

"""XML-RPC APIs for Malone."""

__metaclass__ = type
__all__ = ["FileBugAPI"]

from zope.component import getUtility

from canonical.launchpad.interfaces import IProductSet, IDistributionSet
from canonical.launchpad.webapp import canonical_url, LaunchpadXMLRPCView

class FileBugAPI(LaunchpadXMLRPCView):
    """The XML-RPC API for filing bugs in Malone."""

    def report_bug(self, product, distro, package, title, comment, status,
                   assignee, security_related, private, subscribers):
        if product:
            target = getUtility(IProductSet).getByName(product)
        elif distro:
            target = getUtility(IDistributionSet).getByName(distro)

        bug = target.createBug(
            owner=self.user, title=title, comment=comment)

        return canonical_url(bug)
