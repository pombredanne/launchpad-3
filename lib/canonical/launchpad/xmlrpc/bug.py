# Copyright 2006 Canonical Ltd.  All rights reserved.

"""XML-RPC APIs for Malone."""

__metaclass__ = type
__all__ = ["FileBugAPI"]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProductSet, IPersonSet, IDistributionSet, CreateBugParams)
from canonical.launchpad.webapp import canonical_url, LaunchpadXMLRPCView
from canonical.lp.dbschema import BugTaskStatus

class FileBugAPI(LaunchpadXMLRPCView):
    """The XML-RPC API for filing bugs in Malone."""

    def report_bug(self, product, distro, package, title, comment, status,
                   assignee_email, security_related, private, subscribers):
        if product:
            target = getUtility(IProductSet).getByName(product)
        elif distro:
            target = getUtility(IDistributionSet).getByName(distro)

        # Convert arguments into values that IBugTarget.createBug understands.
        personset = getUtility(IPersonSet)
        if status:
            status = BugTaskStatus.items[status.upper()]
        else:
            status = None
        if assignee_email:
            assignee = personset.getByEmail(assignee_email)
        else:
            assignee = None
        if subscribers:
            subscribers = [personset.getByEmail(p) for p in subscribers]
        else:
            subscribers = []
        if package:
            target = target.getSourcePackage(package)

        private = bool(private)
        security_related = bool(security_related)

        params = CreateBugParams(
            owner=self.user, title=title, comment=comment,
            status=status, assignee=assignee, security_related=security_related,
            private=private, subscribers=subscribers)
        bug = target.createBug(params)

        return canonical_url(bug)
