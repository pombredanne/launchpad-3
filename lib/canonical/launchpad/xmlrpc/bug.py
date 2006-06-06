# Copyright 2006 Canonical Ltd.  All rights reserved.

"""XML-RPC APIs for Malone."""

__metaclass__ = type
__all__ = ["FileBugAPI"]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProductSet, IPersonSet, IDistributionSet, CreateBugParams,
    NotFoundError)
from canonical.launchpad.webapp import canonical_url, LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults
from canonical.lp.dbschema import BugTaskStatus

class FileBugAPI(LaunchpadXMLRPCView):
    """The XML-RPC API for filing bugs in Malone."""

    def filebug(self, product=None, distro=None, package=None, title=None,
                comment=None, status=None, assignee_email=None,
                security_related=None, private=None, subscribers=None):
        if product and distro:
            return faults.FileBugGotProductAndDistro()

        if product:
            target = getUtility(IProductSet).getByName(product)
            if target is None:
                return faults.NoSuchProduct(product)
        elif distro:
            distro_object = getUtility(IDistributionSet).getByName(distro)

            if distro_object is None:
                return faults.NoSuchDistribution(distro)

            if package:
                try:
                    spname, bpname = distro_object.getPackageNames(package)
                except NotFoundError:
                    return faults.NoSuchPackage(package)

                target = distro_object.getSourcePackage(spname)
            else:
                target = distro_object
        else:
            return faults.FileBugMissingProductOrDistribution()

        if not title:
            return faults.RequiredParameterMissing('title')

        if not comment:
            return faults.RequiredParameterMissing('comment')

        if status:
            try:
                BugTaskStatus.items[status.upper()]
            except KeyError:
                return faults.NoSuchStatus(status)

        # Convert arguments into values that IBugTarget.createBug understands.
        personset = getUtility(IPersonSet)
        if status:
            status = BugTaskStatus.items[status.upper()]
        else:
            status = None
        if assignee_email:
            assignee = personset.getByEmail(assignee_email)
            if not assignee:
                return faults.NoSuchPerson(
                    type="assignee", email_address=assignee_email)
        else:
            assignee = None

        subscriber_list = []
        if subscribers:
            for subscriber_email in subscribers:
                subscriber = personset.getByEmail(subscriber_email)
                if not subscriber:
                    return faults.NoSuchPerson(
                        type="subscriber", email_address=subscriber_email)
                else:
                    subscriber_list.append(subscriber)

        private = bool(private)
        security_related = bool(security_related)

        params = CreateBugParams(
            owner=self.user, title=title, comment=comment,
            status=status, assignee=assignee, security_related=security_related,
            private=private, subscribers=subscriber_list)
        bug = target.createBug(params)

        return canonical_url(bug)
