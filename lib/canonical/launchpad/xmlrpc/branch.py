# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = ['IBranchAPI', 'BranchAPI']

from zope.component import getUtility
from zope.interface import Interface, implements
import xmlrpclib

from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.interfaces import (
    IBranchSet, ILaunchBag, IProductSet, IPersonSet)


class IBranchAPI(Interface):
    """XMLRPC external interface for testing the XMLRPC external interface."""

    def register_branch(branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """Register a new branch in Launchpad."""


class BranchAPI(LaunchpadXMLRPCView):

    implements(IBranchAPI)

    def register_branch(self, branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """See IBranchAPI."""
        owner = getUtility(ILaunchBag).user
        if owner is None:
            return xmlrpclib.Fault(
                99, 'Anonymous registration of branches is not supported.')
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

        author = getUtility(IPersonSet).getByEmail(author_email)
        if author is None:
            return xmlrpclib.Fault(
                20, "No such email is registered in Launchpad: %s." % 
                    author_email)

        branch = getUtility(IBranchSet).new(
            name=branch_name, owner=owner, product=product, url=branch_url,
            title=branch_name, summary=branch_description, author=author)

        return u'Successfully registered the branch.'

