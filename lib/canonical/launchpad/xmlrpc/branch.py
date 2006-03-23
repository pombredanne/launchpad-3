# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = ['IBranchSetAPI', 'BranchSetAPI']

from zope.component import getUtility
from zope.interface import Interface, implements
import xmlrpclib

from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.interfaces import (
    IBranchSet, IBugSet, ILaunchBag, IProductSet, IPersonSet, NotFoundError)
from canonical.lp.dbschema import BugBranchStatus


class IBranchSetAPI(Interface):
    """An XMLRPC interface for dealing with branches."""

    def register_branch(branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """Register a new branch in Launchpad."""

    def link_branch_to_bug(branch_url, bug_id, whiteboard):
        """Link the branch to the bug."""


class BranchSetAPI(LaunchpadXMLRPCView):

    implements(IBranchSetAPI)

    def register_branch(self, branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """See IBranchSetAPI."""
        owner = getUtility(ILaunchBag).user
        assert owner is not None, (
            "Anonymous registration of branches is not supported.")
        if product_name:
            product = getUtility(IProductSet).getByName(product_name)
            if product is None:
                return xmlrpclib.Fault(
                    10, "No such product: %s." % product_name)
        else:
            product = None

        if not branch_description:
            # We want it to be None in the database, not ''.
            branch_description = None

        # The branch and title are optional.
        if not branch_name:
            branch_name = branch_url.split('/')[-1]
        if not branch_title:
            branch_title = branch_name

        if author_email:
            author = getUtility(IPersonSet).getByEmail(author_email)
        else:
            author = owner
        if author is None:
            return xmlrpclib.Fault(
                20, "No such email is registered in Launchpad: %s." % 
                    author_email)

        branch = getUtility(IBranchSet).new(
            name=branch_name, owner=owner, product=product, url=branch_url,
            title=branch_name, summary=branch_description, author=author)

        return canonical_url(branch)

    def link_branch_to_bug(self, branch_url, bug_id, whiteboard):
        """See IBranchSetAPI."""
        branch = getUtility(IBranchSet).getByURL(url=branch_url)
        if branch is None:
            return xmlrpclib.Fault(30, 'No such branch: %s' % branch_url)
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            return xmlrpclib.Fault(40, 'No such bug: %s' % bug_id)
        if not whiteboard:
            whiteboard = None

        bug.addBranch(branch, whiteboard=whiteboard)
        return canonical_url(bug)


